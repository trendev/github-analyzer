
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
    """
    A class to represent the analysis of a GitHub repository.

    Attributes:
        name (str): The name of the repository.
        description (Optional[str]): A brief description of the repository.
        language (Optional[str]): The primary programming language used in the repository.
        created_at (datetime): The date and time when the repository was created.
        updated_at (datetime): The date and time when the repository was last updated.
        size_kb (int): The size of the repository in kilobytes.
        stars (int): The number of stars the repository has received.
        forks (int): The number of times the repository has been forked.
        open_issues (int): The number of open issues in the repository.
        has_wiki (bool): Indicates if the repository has a wiki.
        visibility (str): The visibility status of the repository (e.g., public, private).
        archived (bool): Indicates if the repository is archived.
        topics (List[str]): A list of topics associated with the repository.
        default_branch (str): The default branch of the repository.
        license (Optional[str]): The license under which the repository is distributed.
        branch_count (int): The number of branches in the repository.
        contributors_count (int): The number of contributors to the repository.
        url (str): The URL of the repository.
    """
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
    """
    A class to represent statistics of a GitHub organization.

    Attributes:
        total_repos (int): Total number of repositories in the organization.
        active_repos (int): Number of active repositories in the organization.
        archived_repos (int): Number of archived repositories in the organization.
        total_size_kb (int): Total size of all repositories in kilobytes.
        languages (Counter): Counter of programming languages used across repositories.
        topics (Counter): Counter of topics associated with repositories.
        contributors (int): Total number of contributors in the organization.
        forks (int): Total number of forks across all repositories.
        stars (int): Total number of stars across all repositories.
        licenses (Counter): Counter of licenses used across repositories.
    """
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
    """
    A class to analyze GitHub repositories for a given organization and generate a markdown report.
    Methods
    -------
    __init__() -> None:
        Initializes the GithubAnalyzer with environment variables and sets up the GitHub client.
    analyze_repository(repo: Repository, pbar: Optional[tqdm] = None) -> RepositoryAnalysis:
        Analyzes a single repository and returns a RepositoryAnalysis object.
    calculate_org_stats(analyses: List[RepositoryAnalysis]) -> OrganizationStats:
        Calculates and returns statistics for the organization based on the repository analyses.
    generate_markdown_report(analyses: List[RepositoryAnalysis], stats: OrganizationStats) -> str:
        Generates a markdown report based on the repository analyses and organization statistics.
    run_analysis() -> None:
        Runs the analysis for the organization, generates the report, and saves it to a file.
    """

    def __init__(self) -> None:
        load_dotenv()
        self.token = os.getenv("GITHUB_TOKEN")
        self.org_name = os.getenv("GITHUB_ORG")

        if not self.token or not self.org_name:
            raise ValueError(
                "GITHUB_TOKEN and GITHUB_ORG must be set in environment variables")

        self.github = Github(auth=Auth.Token(self.token))
        self.output_dir = Path(os.getenv("OUTPUT_DIR", "reports"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def analyze_repository(self, repo: Repository, pbar: Optional[tqdm] = None) -> RepositoryAnalysis:
        """
        Analyzes a given GitHub repository and returns a detailed analysis.

        Args:
            repo (Repository): The GitHub repository to analyze.
            pbar (Optional[tqdm]): An optional progress bar to update during analysis.

        Returns:
            RepositoryAnalysis: An object containing detailed information about the repository.

        Raises:
            Exception: If there is an error retrieving contributors, sets contributors_count to 0.
        """
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
        """
        Calculate statistics for an organization based on repository analyses.

        Args:
            analyses (List[RepositoryAnalysis]): A list of repository analysis objects.

        Returns:
            OrganizationStats: An object containing various statistics about the organization, including:
                - total_repos (int): Total number of repositories.
                - active_repos (int): Number of active (non-archived) repositories.
                - archived_repos (int): Number of archived repositories.
                - total_size_kb (int): Total size of all repositories in kilobytes.
                - languages (Counter): A counter of programming languages used across repositories.
                - topics (Counter): A counter of topics associated with repositories.
                - contributors (int): Total number of contributors across all repositories.
                - forks (int): Total number of forks across all repositories.
                - stars (int): Total number of stars across all repositories.
                - licenses (Counter): A counter of licenses used across repositories.
        """
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
        """
        Generates a markdown report summarizing the insights of GitHub repositories for an organization.
        Args:
            analyses (List[RepositoryAnalysis]): A list of repository analysis objects containing detailed information about each repository.
            stats (OrganizationStats): An object containing aggregated statistics about the organization's repositories.
        Returns:
            str: A markdown formatted string containing the report.
        The report includes the following sections:
        - Organization Overview: Summary of total, active, and archived repositories, total size, contributors, stars, and forks.
        - Language Distribution: Breakdown of repositories by programming language.
        - Popular Topics: List of the most common topics across repositories.
        - License Distribution: Breakdown of repositories by license type.
        - Active Repositories: Detailed information about each active repository.
        - Archived Repositories: List of archived repositories with basic information.
        Note:
            The report is generated based on the provided analyses and stats, and includes the date and time of generation.
        """
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
            for lic, count in stats.licenses.most_common():
                report += f"- {lic}: {count} repos\n"

        # Active Repositories
        report += "\n## Active Repositories\n"
        for analysis in sorted(analyses, key=lambda x: x.name, reverse=False):
            if analysis.archived:
                continue

            report += f"\n### [{analysis.name}]({analysis.url})\n"
            report += f"**Description:** {analysis.description or 'N/A'}\n"
            report += f"**Language:** {analysis.language or 'N/A'}\n"
            if analysis.topics:
                report += f"**Topics:** {', '.join(analysis.topics)}\n"
            report += "**Statistics:**\n"
            report += f"- Stars: {analysis.stars}\n"
            report += f"- Forks: {analysis.forks}\n"
            report += f"- Contributors: {analysis.contributors_count}\n"
            report += f"- Open Issues: {analysis.open_issues}\n"
            report += f"- Size: {analysis.size_kb/1024:.2f} MB\n"
            report += f"- Branches: {analysis.branch_count}\n"
            report += f"- License: {analysis.license or 'N/A'}\n"
            report += f"**Created:** {
                analysis.created_at.strftime('%Y-%m-%d')}\n"
            report += f"**Last Updated:** {
                analysis.updated_at.strftime('%Y-%m-%d')}\n"

        # Archived Repositories
        if stats.archived_repos > 0:
            report += "\n## Archived Repositories\n"
            for analysis in sorted(analyses, key=lambda x: x.updated_at, reverse=True):
                if not analysis.archived:
                    continue
                report += f"\n### [{analysis.name}]({analysis.url})\n"
                report += f"- Language: {analysis.language or 'N/A'}\n"
                report += f"- Last Updated: {
                    analysis.updated_at.strftime('%Y-%m-%d')}\n"
                if analysis.description:
                    report += f"- Description: {analysis.description}\n"

        report += f"\n---\n*Report generated on: {
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        return report

    def run_analysis(self) -> None:
        """
        Run the analysis for the specified GitHub organization.

        This method performs the following steps:
        1. Fetches the repositories of the organization.
        2. Analyzes each repository and collects analysis results.
        3. Calculates statistics for the organization based on the analysis results.
        4. Generates a markdown report of the analysis.
        5. Saves the report to the specified output directory.
        6. Prints a quick summary of the analysis.

        Progress bars are displayed for fetching repositories, analyzing repositories, and saving the report.

        Raises:
            Exception: If any error occurs during the analysis process.

        Prints:
            Various status messages and progress updates during the analysis.
            A quick summary of the analysis results upon completion.
        """
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
                print(
                    f"- Most Used Language: {stats.languages.most_common(1)[0][0]}")

        except Exception as e:
            print(f"❌ Error during analysis: {str(e)}")
        finally:
            self.github.close()


def main():
    """ Main function """
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
