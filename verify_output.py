import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()


def load_outputs(filepath):
    """Load outputs from JSONL"""
    outputs = {}
    with open(filepath, 'r') as f:
        for line in f:
            data = json.loads(line)
            outputs[data['id']] = data
    return outputs


def verify_format(output, format_hint):
    """Check if answer matches format hint"""
    answer = output['final_answer']
    
    if format_hint == 'int':
        return isinstance(answer, int)
    elif format_hint == 'float':
        return isinstance(answer, (int, float))
    elif format_hint.startswith('list['):
        return isinstance(answer, list)
    elif format_hint.startswith('{'):
        return isinstance(answer, dict)
    
    return False


def verify_citations(output):
    """Check if citations are present"""
    citations = output.get('citations', [])
    return len(citations) > 0


def check_expected_values(outputs):
    """Check against known correct answers"""
    checks = {
        'rag_policy_beverages_return_days': {
            'expected': 14,
            'tolerance': 0
        },
        'hybrid_aov_winter_1997': {
            'expected': None,  
            'min': 100.0,
            'max': 2000.0
        },
        'sql_top3_products_by_revenue_alltime': {
            'expected_type': list,
            'expected_length': 3
        }
    }
    
    results = {}
    for qid, check in checks.items():
        if qid not in outputs:
            results[qid] = {'status': 'missing', 'message': 'Output not found'}
            continue
        
        output = outputs[qid]
        answer = output['final_answer']

        if 'expected' in check and check['expected'] is not None:
            if answer == check['expected']:
                results[qid] = {'status': 'pass', 'message': f'Correct: {answer}'}
            else:
                results[qid] = {'status': 'fail', 'message': f'Expected {check["expected"]}, got {answer}'}

        elif 'min' in check and 'max' in check:
            if isinstance(answer, (int, float)) and check['min'] <= answer <= check['max']:
                results[qid] = {'status': 'pass', 'message': f'In range: {answer}'}
            else:
                results[qid] = {'status': 'fail', 'message': f'Out of range: {answer}'}

        elif 'expected_type' in check:
            if isinstance(answer, check['expected_type']):
                if 'expected_length' in check:
                    if len(answer) == check['expected_length']:
                        results[qid] = {'status': 'pass', 'message': f'Correct type and length: {len(answer)}'}
                    else:
                        results[qid] = {'status': 'fail', 'message': f'Wrong length: {len(answer)} vs {check["expected_length"]}'}
                else:
                    results[qid] = {'status': 'pass', 'message': 'Correct type'}
            else:
                results[qid] = {'status': 'fail', 'message': f'Wrong type: {type(answer).__name__}'}
    
    return results


def main():
    console.print("[bold cyan]Output Verification[/bold cyan]\n")

    outputs_file = 'outputs_hybrid.jsonl'
    if not Path(outputs_file).exists():
        console.print(f"[red]✗[/red] Output file not found: {outputs_file}")
        console.print("Run: python run_agent_hybrid.py --batch sample_questions_hybrid_eval.jsonl --out outputs_hybrid.jsonl")
        return

    console.print(f"Loading {outputs_file}...")
    outputs = load_outputs(outputs_file)
    console.print(f"[green]✓[/green] Loaded {len(outputs)} outputs\n")

    with open('sample_questions_hybrid_eval.jsonl', 'r') as f:
        questions = [json.loads(line) for line in f]

    table = Table(title="Verification Results")
    table.add_column("Question ID", style="cyan")
    table.add_column("Format", style="magenta")
    table.add_column("Citations", style="yellow")
    table.add_column("Confidence", style="blue")
    table.add_column("Status", style="green")

    for q in questions:
        qid = q['id']
        format_hint = q['format_hint']
        
        if qid not in outputs:
            table.add_row(qid, format_hint, "✗", "-", "[red]Missing[/red]")
            continue
        
        output = outputs[qid]

        format_ok = verify_format(output, format_hint)
        format_status = "[green]✓[/green]" if format_ok else "[red]✗[/red]"

        citations_ok = verify_citations(output)
        citation_status = "[green]✓[/green]" if citations_ok else "[red]✗[/red]"

        confidence = output.get('confidence', 0.0)
        conf_str = f"{confidence:.2f}"

        if format_ok and citations_ok:
            status = "[green]Pass[/green]"
        else:
            status = "[red]Fail[/red]"
        
        table.add_row(qid, format_status, citation_status, conf_str, status)
    
    console.print(table)

    console.print("\n[bold]Checking Expected Values:[/bold]\n")
    value_checks = check_expected_values(outputs)
    
    for qid, result in value_checks.items():
        status_color = "green" if result['status'] == 'pass' else "red"
        console.print(f"[{status_color}]{result['status'].upper()}[/{status_color}] {qid}: {result['message']}")

    console.print("\n[bold]Summary:[/bold]")
    total = len(questions)
    completed = len(outputs)
    
    format_passed = sum(1 for q in questions if q['id'] in outputs and verify_format(outputs[q['id']], q['format_hint']))
    citations_passed = sum(1 for q in questions if q['id'] in outputs and verify_citations(outputs[q['id']]))
    
    console.print(f"  Total questions: {total}")
    console.print(f"  Completed: {completed}/{total}")
    console.print(f"  Format valid: {format_passed}/{completed}")
    console.print(f"  Has citations: {citations_passed}/{completed}")

    overall = (format_passed + citations_passed) / (2 * total) * 100
    console.print(f"\n  [bold]Overall Score: {overall:.1f}%[/bold]")


if __name__ == "__main__":
    main()