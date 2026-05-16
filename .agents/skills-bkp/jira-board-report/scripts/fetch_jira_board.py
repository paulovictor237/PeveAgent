#!/usr/bin/env python3
import json
import subprocess
import sys
from datetime import datetime
from typing import List, Dict, Any

# Team members to mention with @
TEAM_MEMBERS = [
    "Daniel Boso",
    "Gabriel Reinert",
    "peve",  # PeVe (Paulo Victor)
    "João Pedro de Lima Cordeiro",
    "Lucas Leal dos Santos",
    "Priscila Batisti"
]

TEAM_MAPPING = {
    "Daniel Boso": "@Daniel Boso",
    "Gabriel Reinert": "@Gabriel Reinert",
    "peve": "@PeVe (Paulo Victor)",
    "João Pedro de Lima Cordeiro": "@João Pedro Cordeiro",
    "Lucas Leal dos Santos": "@Lucas Leal",
    "Priscila Batisti": "@Priscila Batisti"
}

# Column/Status mapping
# Hierarquia de prioridade conforme solicitado: 
# 1. Waiting deploy (Waiting Deploy)
# 2. TESTING & MERGE (Validation)
# 3. TO TEST (Testar)
# 4. CODE REVIEW (Code Review)
# 5. IN PROGRESS (Em andamento)
COLUMNS = [
    {"label": "Waiting deploy", "status": "Waiting Deploy"},
    {"label": "TESTING & MERGE", "status": "Validation"},
    {"label": "TO TEST", "status": "Testar"},
    {"label": "CODE REVIEW", "status": "Code Review"},
    {"label": "IN PROGRESS", "status": "Em andamento"}
]

def run_acli(args: List[str]) -> str:
    cmd = ["acli"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running acli: {result.stderr}", file=sys.stderr)
        return ""
    return result.stdout

def get_issue_details(key: str) -> Dict[str, Any]:
    output = run_acli(["jira", "workitem", "view", key, "--fields", "*all", "--json"])
    if not output:
        return {}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {}

def get_issues() -> List[Dict[str, Any]]:
    # Use both names for status in JQL to be safe with localization
    jql_statuses = set()
    for c in COLUMNS:
        jql_statuses.add(c["status"])
        if c["status"] == "Em andamento":
            jql_statuses.add("In Progress")
    
    statuses_str = ",".join([f"'{s}'" for s in jql_statuses])
    # Include all issue types to ensure no tasks are missed
    jql = f"project = APX AND status in ({statuses_str})"
    
    output = run_acli(["jira", "workitem", "search", "--jql", jql, "--limit", "100", "--json"])
    if not output:
        return []
    try:
        basic_issues = json.loads(output)
        detailed_issues = []
        for issue in basic_issues:
            # Re-fetch for all details as in original script
            details = get_issue_details(issue["key"])
            if details:
                detailed_issues.append(details)
        return detailed_issues
    except json.JSONDecodeError:
        return []

def format_date(date_str: str) -> str:
    if not date_str:
        return ""
    # Jira dates are like "2026-02-13T16:07:58.950-0300"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return date_str[:10]

def calculate_days(date_str: str) -> int:
    if not date_str:
        return 0
    try:
        # Jira dates: 2026-02-13T16:07:58.950-0300
        # datetime.fromisoformat needs a colon in the timezone offset for some Python versions
        # e.g. -03:00 instead of -0300
        if len(date_str) > 5 and date_str[-5] in ('+', '-'):
            date_str = date_str[:-2] + ':' + date_str[-2:]
            
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        # Make now aware if dt is aware
        now = datetime.now(dt.tzinfo)
        delta = now - dt
        return max(0, delta.days)
    except Exception as e:
        # print(f"Error calculating days for {date_str}: {e}", file=sys.stderr)
        return 0

def get_assignee_name(issue: Dict[str, Any]) -> str:
    assignee = issue.get("fields", {}).get("assignee")
    if not assignee:
        return "Ninguém"
    
    display_name = assignee.get("displayName", "")
    return TEAM_MAPPING.get(display_name, display_name)

import argparse

# ... (TEAM_MEMBERS and TEAM_MAPPING remain same)

def generate_report(include_in_progress=False):
    issues = get_issues()
    
    # Group issues by status
    by_status = {c["status"]: [] for c in COLUMNS}
    for issue in issues:
        status_name = issue.get("fields", {}).get("status", {}).get("name")
        if status_name in by_status:
            by_status[status_name].append(issue)
        elif status_name == "In Progress": # Match JQL fallback
            by_status["Em andamento"].append(issue)
    
    report_lines = []
    
    for col in COLUMNS:
        status_name = col["status"]
        label = col["label"]
        
        # Skip IN PROGRESS if not requested
        if label == "IN PROGRESS" and not include_in_progress:
            continue
            
        issues_in_col = by_status[status_name]
        
        if not issues_in_col:
            continue
            
        report_lines.append(f"*{label}*\n")
        
        for i, issue in enumerate(issues_in_col, 1):
            key = issue.get("key")
            summary = issue.get("fields", {}).get("summary") or "Sem título"
            assignee = get_assignee_name(issue)
            
            status_changed = issue.get("fields", {}).get("statuscategorychangedate")
            created = issue.get("fields", {}).get("created")
            
            days_in_col = calculate_days(status_changed)
            since_date = format_date(status_changed)
            
            days_in_progress = calculate_days(created)
            start_date = format_date(created)
            
            report_lines.append(f"*{summary} ({key})*")
            report_lines.append(f"• *Link:* `https://motoristapx.atlassian.net/browse/{key}|{key}`")
            report_lines.append(f"• *Responsável:* {assignee}")
            report_lines.append(f"• *Dias em andamento:* *{days_in_progress} dias* (Início: {start_date})")
            report_lines.append(f"• *Dias parado na coluna atual:* *{days_in_col} dias* (Desde: {since_date})\n")

    print("\n".join(report_lines))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera relatório do Jira para Slack.")
    parser.add_argument("--in-progress", action="store_true", help="Inclui tarefas em andamento")
    args = parser.parse_args()
    
    generate_report(include_in_progress=args.in_progress)
