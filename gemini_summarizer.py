import os
from typing import List, Dict, Optional
from dataclasses import dataclass
from google import genai
from google.genai import types
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
import re
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()


@dataclass
class ArticleForSummary:
    title: str
    content: str
    feed_title: str
    category: str
    published: str
    link: str
    
    @property
    def word_count(self) -> int:
        """Count words in title and content."""
        text = f"{self.title} {self.content}"
        # Simple word count: split by whitespace and filter empty strings
        words = [w for w in re.split(r'\s+', text) if w]
        return len(words)
    
    @property
    def estimated_tokens(self) -> int:
        """Estimate token count as word count * 1.34."""
        return int(self.word_count * 1.34)


class GeminiSummarizer:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.console = Console()
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        
        if not self.api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY environment variable or pass api_key parameter.")
        
        # Initialize the client with the API key
        self.client = genai.Client(api_key=self.api_key)
        
        # Use model from environment or parameter, defaulting to GEMINI_MODEL_SUMMARIES
        self.model_name = model_name or os.environ.get('GEMINI_MODEL_SUMMARIES', 'gemini-pro')
        
        self.console.print(f"[dim]Using Gemini model: {self.model_name}[/dim]")
        
        # Load the prompt template
        self.prompt_template = self._load_prompt_template()
        
        # Load the title generation prompt
        self.title_prompt_template = self._load_title_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load the prompt template from prompt_summarize.md file."""
        prompt_file = os.path.join(os.path.dirname(__file__), 'prompt_summarize.md')
        
        if not os.path.exists(prompt_file):
            # Try parent directory if not in same directory
            prompt_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompt_summarize.md')
        
        if os.path.exists(prompt_file):
            with open(prompt_file, 'r') as f:
                return f.read()
        else:
            raise FileNotFoundError(f"Could not find prompt_summarize.md file. Looked in: {prompt_file}")
    
    def _load_title_prompt_template(self) -> str:
        """Load the title generation prompt from prompt_generate-title.md file."""
        prompt_file = os.path.join(os.path.dirname(__file__), 'prompt_generate-title.md')
        
        if not os.path.exists(prompt_file):
            # Try parent directory if not in same directory
            prompt_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompt_generate-title.md')
        
        if os.path.exists(prompt_file):
            with open(prompt_file, 'r') as f:
                return f.read()
        else:
            # Return default prompt if file not found
            return "Create a title from the most important development listed in the report that is no more than 10 words in length. Output only the title, nothing else."
    
    def prepare_articles_for_summary(self, articles: List) -> List[ArticleForSummary]:
        """Convert articles to format suitable for summarization."""
        prepared = []
        for article in articles:
            # Combine title and summary for content
            content = article.summary if article.summary else ""
            
            prepared.append(ArticleForSummary(
                title=article.title,
                content=content,
                feed_title=article.feed_title,
                category=article.category or "Uncategorized",
                published=article.published.strftime("%Y-%m-%d %H:%M"),
                link=article.link
            ))
        
        return prepared
    
    def display_token_summary(self, articles: List[ArticleForSummary]) -> int:
        """Display token count summary and return total tokens."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Feed", style="green", width=30)
        table.add_column("Title", style="white", width=50)
        table.add_column("Words", style="cyan", justify="right")
        table.add_column("Est. Tokens", style="yellow", justify="right")
        
        total_words = 0
        total_tokens = 0
        
        for article in articles:
            table.add_row(
                article.feed_title[:30],
                article.title[:50] + ("..." if len(article.title) > 50 else ""),
                str(article.word_count),
                str(article.estimated_tokens)
            )
            total_words += article.word_count
            total_tokens += article.estimated_tokens
        
        self.console.print("\n[bold]Token Count Summary[/bold]\n")
        self.console.print(table)
        self.console.print(f"\n[bold]Total: {total_words:,} words ≈ {total_tokens:,} tokens[/bold]")
        
        # Gemini Pro has a context window of 1MM tokens
        if total_tokens > 750000:
            self.console.print(f"\n[yellow]Warning: Total tokens ({total_tokens:,}) approaching Gemini Pro limit (1MM)[/yellow]")
        
        return total_tokens
    
    def create_prompt_with_articles(self, articles: List[ArticleForSummary]) -> str:
        """Create the full prompt by combining template with article data."""
        # Start with the prompt template
        prompt = self.prompt_template + "\n\n---\n\nARTICLES TO SUMMARIZE:\n\n"
        
        # Add article data
        for i, article in enumerate(articles, 1):
            prompt += f"{i}. [{article.category}] {article.feed_title} ({article.published})\n"
            prompt += f"   Title: {article.title}\n"
            prompt += f"   URL: {article.link}\n"
            if article.content:
                prompt += f"   Summary: {article.content}\n"
            prompt += "\n"
        
        prompt += "\n---\n\nPlease provide the two-part summary as specified above."
        
        return prompt
    
    def summarize_articles(self, articles: List[ArticleForSummary]) -> str:
        """Summarize articles using Gemini with the loaded prompt template."""
        prompt = self.create_prompt_with_articles(articles)
        
        try:
            # Create content structure for the API
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            
            # Configure generation with thinking enabled and max output tokens
            generate_content_config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_budget=-1,  # Extended thinking
                ),
                response_mime_type="text/plain",
                candidate_count=1,
                max_output_tokens=64000,  # Set max output tokens to 64k
            )
            
            # Collect the full response from the stream
            full_response = ""
            chunk_count = 0
            last_chunk_time = None
            
            self.console.print("[dim]Receiving response from Gemini...[/dim]")
            
            for chunk in self.client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=generate_content_config,
            ):
                if chunk.text:
                    chunk_count += 1
                    full_response += chunk.text
                    last_chunk_time = datetime.now()
                    
                    # Log progress every 10 chunks
                    if chunk_count % 10 == 0:
                        self.console.print(f"[dim]Received {chunk_count} chunks, {len(full_response):,} chars...[/dim]")
            
            self.console.print(f"[dim]Completed: {chunk_count} chunks, {len(full_response):,} total chars[/dim]")
            
            if not full_response:
                raise Exception("No response generated from Gemini API")
            
            # Check if response seems complete
            if len(full_response) < 1000:
                self.console.print(f"[yellow]Warning: Response seems unusually short ({len(full_response)} chars)[/yellow]")
            
            # Check if response was cut off (doesn't end with proper punctuation or markdown)
            last_chars = full_response.strip()[-100:]
            if not any(last_chars.endswith(ending) for ending in ['.', '!', '?', '\n', ')', ']', '}']):
                self.console.print("[yellow]Warning: Response may have been cut off[/yellow]")
                self.console.print(f"[dim]Last 100 chars: ...{last_chars}[/dim]")
                
            return full_response
            
        except Exception as e:
            raise Exception(f"Error calling Gemini API: {str(e)}")
    
    def interactive_summarize(self, articles: List, show_cost_estimate: bool = True) -> Optional[str]:
        """Interactive summarization with token count display and user confirmation."""
        if not articles:
            self.console.print("[yellow]No articles to summarize.[/yellow]")
            return None
        
        # Prepare articles
        prepared_articles = self.prepare_articles_for_summary(articles)
        
        # Display token summary
        total_tokens = self.display_token_summary(prepared_articles)
        
        if show_cost_estimate:
            # Calculate approximate cost based on model (Paid Tier pricing)
            # Updated Gemini pricing from ai.google.dev/gemini-api/docs/pricing
            
            if 'flash-lite' in self.model_name.lower():
                # Gemini 2.5 Flash-Lite pricing (per 1M tokens)
                input_price = 0.10   # $0.10 per 1M tokens
                output_price = 0.40  # $0.40 per 1M tokens
                model_display = "Gemini 2.5 Flash-Lite"
            elif 'flash' in self.model_name.lower():
                # Gemini 2.5 Flash pricing (per 1M tokens)
                input_price = 0.30   # $0.30 per 1M tokens
                output_price = 2.50  # $2.50 per 1M tokens
                model_display = "Gemini 2.5 Flash"
            else:
                # Gemini 2.5 Pro pricing (per 1M tokens)
                # Assumes prompts <= 200k tokens
                input_price = 1.25   # $1.25 per 1M tokens
                output_price = 10.00 # $10.00 per 1M tokens
                model_display = "Gemini 2.5 Pro"
            
            # Estimate output as 20% of input
            input_cost = (total_tokens / 1_000_000) * input_price
            output_tokens_est = int(total_tokens * 0.2)
            output_cost = (output_tokens_est / 1_000_000) * output_price
            total_cost_est = input_cost + output_cost
            
            self.console.print(f"\n[dim]Estimated cost for {model_display}: ${total_cost_est:.6f} (input: ${input_cost:.6f}, output: ${output_cost:.6f})[/dim]")
            self.console.print(f"[dim]Input: {total_tokens:,} tokens @ ${input_price}/1M | Output: ~{output_tokens_est:,} tokens @ ${output_price}/1M[/dim]")
        
        # Show preview of what will be sent
        self.console.print(f"\n[bold]Will summarize {len(prepared_articles)} articles[/bold]")
        self.console.print("The summary will follow the format specified in prompt_summarize.md:")
        self.console.print("- Top 3 Most Important Developments")
        self.console.print("- Thematic Summary of all other headlines")
        
        # Ask for confirmation
        if not Confirm.ask("\nProceed with summarization?"):
            return None
        
        # Perform summarization
        self.console.print("\n[bold blue]Generating summary using Gemini...[/bold blue]")
        
        try:
            summary = self.summarize_articles(prepared_articles)
            return summary
        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/red]")
            return None
    
    def estimate_tokens_for_prompt(self, prompt: str) -> int:
        """Estimate tokens for a given prompt string."""
        words = [w for w in re.split(r'\s+', prompt) if w]
        return int(len(words) * 1.34)
    
    def generate_title(self, summary: str) -> str:
        """Generate a title for the summary using Gemini Flash-Lite."""
        # Use the title generation model from .env
        title_model = os.environ.get('GEMINI_MODEL_TITLES', 'gemini-2.5-flash-lite-preview-06-17')
        
        # Combine the title prompt with the summary
        prompt = f"{self.title_prompt_template}\n\n---\n\nREPORT:\n\n{summary}"
        
        try:
            # Create content structure for the API
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            
            # Configure generation for title (short response expected)
            generate_content_config = types.GenerateContentConfig(
                response_mime_type="text/plain",
                candidate_count=1,
                max_output_tokens=100,  # Title should be short
            )
            
            # Generate title
            full_response = ""
            for chunk in self.client.models.generate_content_stream(
                model=title_model,
                contents=contents,
                config=generate_content_config,
            ):
                if chunk.text:
                    full_response += chunk.text
            
            # Clean up the title (remove quotes, extra whitespace)
            title = full_response.strip()
            title = title.strip('"').strip("'").strip()
            
            # Ensure title is not too long
            words = title.split()
            if len(words) > 10:
                title = ' '.join(words[:10])
            
            return title
            
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not generate title: {str(e)}[/yellow]")
            return "News Summary"