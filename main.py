from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from github import Github, Repository, Auth
import os
from dotenv import load_dotenv

@dataclass
class RepositoryAnalysis:
    name: str
    description: Optional[str]
    language: Optional[str]
    created_at: datetime
    updated_at: datetime
    size_kb: int
    stars: int
    forks: int
    open_issues: int
    has_wiki: bool
    visibility: str
    archived: bool

class GithubAnalyzer:
    def __init__(self) -> None:
        load_dotenv()
        self.token = os.getenv("GITHUB_TOKEN")
        self.org_name = os.getenv("GITHUB_ORG")
        
        if not self.token or not self.org_name:
            raise ValueError("GITHUB_TOKEN and GITHUB_ORG must be set in environment variables")
        
        self.github = Github(auth=Auth.Token(self.token))
        self.output_dir = Path(os.getenv("OUTPUT_DIR", "reports"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def analyze_repository(self, repo: Repository) -> RepositoryAnalysis:
        return RepositoryAnalysis(
            name=repo.name,
            description=repo.description,
            language=repo.language,
            created_at=repo.created_at,
            updated_at=repo.updated_at,
            size_kb=repo.size,
            stars=repo.stargazers_count,
            forks=repo.forks_count,
            open_issues=repo.open_issues_count,
            has_wiki=repo.has_wiki,
            visibility=repo.visibility,
            archived=repo.archived
        )

    def generate_markdown_report(self, analyses: List[RepositoryAnalysis]) -> str:
        report = "# Organization Repository Analysis\n\n"
        
        report += f"## Overview\n"
        report += f"- Organization: {self.org_name}\n"
        report += f"- Total Repositories: {len(analyses)}\n"
        report += f"- Active Repositories: {sum(1 for a in analyses if not a.archived)}\n"
        
        languages = {}
        for analysis in analyses:
            if analysis.language:
                languages[analysis.language] = languages.get(analysis.language, 0) + 1
        
        report += "\n## Language Distribution\n"
        for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(analyses)) * 100
            report += f"- {lang}: {count} repositories ({percentage:.1f}%)\n"
        
        report += "\n## Active Repositories\n"
        for analysis in sorted(analyses, key=lambda x: x.updated_at, reverse=True):
            if analysis.archived:
                continue
            
            report += f"\n### {analysis.name}\n"
            report += f"**Description:** {analysis.description or 'N/A'}\n"
            report += f"**Language:** {analysis.language or 'N/A'}\n"
            report += f"**Statistics:**\n"
            report += f"- Stars: {analysis.stars}\n"
            report += f"- Forks: {analysis.forks}\n"
            report += f"- Open Issues: {analysis.open_issues}\n"
            report += f"- Size: {analysis.size_kb/1024:.2f} MB\n"
            report += f"**Created:** {analysis.created_at.strftime('%Y-%m-%d')}\n"
            report += f"**Last Updated:** {analysis.updated_at.strftime('%Y-%m-%d')}\n"
        
        report += f"\n*Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        return report

    def run_analysis(self) -> None:
        try:
            org = self.github.get_organization(self.org_name)
            repos = list(org.get_repos())
            analyses = [self.analyze_repository(repo) for repo in repos]
            
            report = self.generate_markdown_report(analyses)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = self.output_dir / f'github_analysis_{timestamp}.md'
            
            report_path.write_text(report, encoding='utf-8')
            print(f"Analysis complete. Report saved to: {report_path}")
            
        except Exception as e:
            print(f"Error during analysis: {str(e)}")
        finally:
            self.github.close()

if __name__ == "__main__":
    analyzer = GithubAnalyzer()
    analyzer.run_analysis()
