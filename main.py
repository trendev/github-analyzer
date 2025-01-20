import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Counter, List, Optional

from dotenv import load_dotenv
from github import Auth, Github, Repository
from tqdm import tqdm


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
    topics: List[str]
    default_branch: str
    license: Optional[str]
    branch_count: int
    contributors_count: int
    url: str

@dataclass
class OrganizationStats:
    total_repos: int
    active_repos: int
    archived_repos: int
    total_size_kb: int
    languages: Counter
    topics: Counter
    contributors: int
    forks: int
    stars: int
    licenses: Counter

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

    def analyze_repository(self, repo: Repository, pbar: Optional[tqdm] = None) -> RepositoryAnalysis:
        if pbar:
            pbar.set_description(f"Analyzing {repo.name}")
        
        try:
            contributors_count = sum(1 for _ in repo.get_contributors())
        except Exception:
            contributors_count = 0

        analysis = RepositoryAnalysis(
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
            archived=repo.archived,
            topics=repo.get_topics(),
            default_branch=repo.default_branch,
            license=repo.license.name if repo.license else None,
            branch_count=sum(1 for _ in repo.get_branches()),
            contributors_count=contributors_count,
            url=repo.html_url
        )

        if pbar:
            pbar.update(1)
        
        return analysis

    def calculate_org_stats(self, analyses: List[RepositoryAnalysis]) -> OrganizationStats:
        languages = Counter()
        topics = Counter()
        licenses = Counter()
        total_contributors = 0
        total_forks = 0
        total_stars = 0
        total_size = 0

        for analysis in analyses:
            if analysis.language:
                languages[analysis.language] += 1
            for topic in analysis.topics:
                topics[topic] += 1
            if analysis.license:
                licenses[analysis.license] += 1
            
            total_contributors += analysis.contributors_count
            total_forks += analysis.forks
            total_stars += analysis.stars
            total_size += analysis.size_kb

        return OrganizationStats(
            total_repos=len(analyses),
            active_repos=sum(1 for a in analyses if not a.archived),
            archived_repos=sum(1 for a in analyses if a.archived),
            total_size_kb=total_size,
            languages=languages,
            topics=topics,
            contributors=total_contributors,
            forks=total_forks,
            stars=total_stars,
            licenses=licenses
        )

    def generate_markdown_report(self, analyses: List[RepositoryAnalysis], stats: OrganizationStats) -> str:
        report = f"# {self.org_name} / GitHub Repositories Insights Report\n\n"
        
        # Organization Overview
        report += "## Organization Overview\n"
        report += f"- Total Repositories: {stats.total_repos}\n"
        report += f"- Active Repositories: {stats.active_repos}\n"
        report += f"- Archived Repositories: {stats.archived_repos}\n"
        report += f"- Total Size: {stats.total_size_kb/1024:.2f} MB\n"
        report += f"- Total Contributors: {stats.contributors}\n"
        report += f"- Total Stars: {stats.stars}\n"
        report += f"- Total Forks: {stats.forks}\n\n"

        # Language Distribution
        report += "## Language Distribution\n"
        for lang, count in stats.languages.most_common():
            percentage = (count / stats.total_repos) * 100
            report += f"- {lang}: {count} repos ({percentage:.1f}%)\n"
        
        # Popular Topics
        if stats.topics:
            report += "\n## Popular Topics\n"
            for topic, count in stats.topics.most_common(10):
                report += f"- {topic}: {count} repos\n"

        # License Distribution
        if stats.licenses:
            report += "\n## License Distribution\n"
            for license, count in stats.licenses.most_common():
                report += f"- {license}: {count} repos\n"

        # Active Repositories
        report += "\n## Active Repositories\n"
        for analysis in sorted(analyses, key=lambda x: x.updated_at, reverse=True):
            if analysis.archived:
                continue
            
            report += f"\n### [{analysis.name}]({analysis.url})\n"
            report += f"**Description:** {analysis.description or 'N/A'}\n"
            report += f"**Language:** {analysis.language or 'N/A'}\n"
            if analysis.topics:
                report += f"**Topics:** {', '.join(analysis.topics)}\n"
            report += f"**Statistics:**\n"
            report += f"- Stars: {analysis.stars}\n"
            report += f"- Forks: {analysis.forks}\n"
            report += f"- Contributors: {analysis.contributors_count}\n"
            report += f"- Open Issues: {analysis.open_issues}\n"
            report += f"- Size: {analysis.size_kb/1024:.2f} MB\n"
            report += f"- Branches: {analysis.branch_count}\n"
            report += f"- License: {analysis.license or 'N/A'}\n"
            report += f"**Created:** {analysis.created_at.strftime('%Y-%m-%d')}\n"
            report += f"**Last Updated:** {analysis.updated_at.strftime('%Y-%m-%d')}\n"

        # Archived Repositories
        if stats.archived_repos > 0:
            report += "\n## Archived Repositories\n"
            for analysis in sorted(analyses, key=lambda x: x.updated_at, reverse=True):
                if not analysis.archived:
                    continue
                report += f"\n### [{analysis.name}]({analysis.url})\n"
                report += f"- Language: {analysis.language or 'N/A'}\n"
                report += f"- Last Updated: {analysis.updated_at.strftime('%Y-%m-%d')}\n"
                if analysis.description:
                    report += f"- Description: {analysis.description}\n"

        report += f"\n---\n*Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        return report

    def run_analysis(self) -> None:
        try:
            print(f"📊 Starting analysis for organization: {self.org_name}")
            
            # Get organization and repos with progress bar
            print("🔍 Fetching repositories...")
            org = self.github.get_organization(self.org_name)
            repos = list(org.get_repos())
            total_repos = len(repos)
            
            print(f"Found {total_repos} repositories")
            time.sleep(1)  # Small pause for better UX
            
            # Analyze repositories with progress bar
            analyses = []
            with tqdm(total=total_repos, desc="Analyzing repositories", 
                     unit="repo", ncols=100) as pbar:
                for repo in repos:
                    analysis = self.analyze_repository(repo, pbar)
                    analyses.append(analysis)
            
            print("📈 Calculating organization statistics...")
            stats = self.calculate_org_stats(analyses)
            
            print("📝 Generating report...")
            report = self.generate_markdown_report(analyses, stats)
            
            # Save report with progress bar
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = self.output_dir / f'{self.org_name}_{timestamp}.md'
            
            with tqdm(total=1, desc="Saving report", ncols=100) as pbar:
                report_path.write_text(report, encoding='utf-8')
                pbar.update(1)
            
            print(f"✅ Analysis complete! Report saved to: {report_path}")
            
            # Print some quick stats
            print("\n📊 Quick Summary:")
            print(f"- Total Repositories: {stats.total_repos}")
            print(f"- Active Repositories: {stats.active_repos}")
            print(f"- Total Contributors: {stats.contributors}")
            if stats.languages:
                print(f"- Most Used Language: {stats.languages.most_common(1)[0][0]}")
            
        except Exception as e:
            print(f"❌ Error during analysis: {str(e)}")
        finally:
            self.github.close()

def main():
    try:
        print("🚀 GitHub Organization Analyzer")
        analyzer = GithubAnalyzer()
        analyzer.run_analysis()
    except KeyboardInterrupt:
        print("\n⚠️ Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
