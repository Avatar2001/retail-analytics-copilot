"""Main entry point for the retail analytics agent."""
import click
import json
import dspy
from pathlib import Path
from rich.console import Console
from rich.progress import track
import sys

from agent.graph_hybrid import HybridAgent

console = Console()


def setup_ollama_lm(model: str = "phi3.5:3.8b-mini-instruct-q4_K_M"):
    """Setup Ollama language model."""
    try:
        lm = dspy.OllamaLocal(
            model=model,
            max_tokens=1000,
            temperature=0.1
        )
        return lm
    except Exception as e:
        console.print(f"[red]Error setting up Ollama: {e}[/red]")
        console.print("[yellow]Make sure Ollama is installed and the model is pulled:[/yellow]")
        console.print(f"  ollama pull {model}")
        sys.exit(1)


@click.command()
@click.option('--batch', required=True, help='Path to JSONL file with questions')
@click.option('--out', required=True, help='Path to output JSONL file')
@click.option('--db', default='data/northwind.sqlite', help='Path to database')
@click.option('--docs', default='docs', help='Path to docs directory')
@click.option('--model', default='phi3.5:3.8b-mini-instruct-q4_K_M', help='Ollama model name')
def main(batch: str, out: str, db: str, docs: str, model: str):
    """Run the retail analytics agent on a batch of questions."""
    
    console.print("[bold blue]Retail Analytics Copilot[/bold blue]")
    console.print(f"Database: {db}")
    console.print(f"Docs: {docs}")
    console.print(f"Model: {model}\n")
    
    # Setup language model
    console.print("[yellow]Setting up language model...[/yellow]")
    lm = setup_ollama_lm(model)
    
    # Initialize agent
    console.print("[yellow]Initializing agent...[/yellow]")
    agent = HybridAgent(db_path=db, docs_dir=docs, lm=lm)
    
    # Load questions
    console.print(f"[yellow]Loading questions from {batch}...[/yellow]")
    questions = []
    with open(batch, 'r') as f:
        for line in f:
            questions.append(json.loads(line))
    
    console.print(f"[green]Loaded {len(questions)} questions[/green]\n")
    
    # Process questions
    results = []
    for q in track(questions, description="Processing questions..."):
        console.print(f"\n[cyan]Question: {q['id']}[/cyan]")
        console.print(f"  {q['question']}")
        
        try:
            result = agent.run(
                question=q['question'],
                format_hint=q['format_hint']
            )
            
            output = {
                "id": q['id'],
                "final_answer": result['final_answer'],
                "sql": result.get('sql', ''),
                "confidence": result.get('confidence', 0.0),
                "explanation": result.get('explanation', ''),
                "citations": result.get('citations', [])
            }
            
            console.print(f"[green]  Answer: {output['final_answer']}[/green]")
            console.print(f"  Confidence: {output['confidence']:.2f}")
            
            results.append(output)
            
        except Exception as e:
            console.print(f"[red]  Error: {e}[/red]")
            import traceback
            traceback.print_exc()
            
            # Add error result
            results.append({
                "id": q['id'],
                "final_answer": None,
                "sql": "",
                "confidence": 0.0,
                "explanation": f"Error: {str(e)}",
                "citations": []
            })
    
    # Write results
    console.print(f"\n[yellow]Writing results to {out}...[/yellow]")
    with open(out, 'w') as f:
        for result in results:
            f.write(json.dumps(result) + '\n')
    
    console.print(f"[bold green]Done! Results written to {out}[/bold green]")


if __name__ == '__main__':
    main()
