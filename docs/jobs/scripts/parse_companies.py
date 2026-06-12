import re
from pathlib import Path

def extract_companies(md_path: Path):
    content = md_path.read_text()
    
    # Match ## headers and everything until the next ## header or end of file
    sections = re.findall(r'## ([^\n]+)\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    
    companies_by_category = {}
    for header, section_content in sections:
        header = header.strip()
        if "Job Search" in header:
            continue
        companies = []
        for line in section_content.split('\n'):
            # Match bullet points (e.g., "- Cisco — R&D center")
            match = re.match(r'^\s*-\s*([^—\-\(]+)', line)
            if match:
                company_name = match.group(1).strip()
                if company_name:
                    companies.append(company_name)
        if companies:
            companies_by_category[header] = companies
            
    return companies_by_category

if __name__ == "__main__":
    # Resolve absolute path to docs/jobs/irlanda.md
    md_file = Path("/Users/paulo.duarte/workspace/outros/PeveAgent/docs/jobs/irlanda.md")
    companies = extract_companies(md_file)
    total = sum(len(c) for c in companies.values())
    print(f"Total companies extracted: {total}")
    for cat, list_c in companies.items():
        print(f"\n{cat} ({len(list_c)} companies):")
        for c in list_c:
            print(f"  - {c}")
