from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Literal
from datetime import datetime
import sys
sys.path.append("..")  # 添加上级目录到模块搜索路径
from clients.generic_client import GenericClient

class GenericProcessor(ABC):
    model_name: str
    temperature: float
    max_tokens: int
    api_key: Optional[str]
    base_url: str
    prompts: Dict[str, str] = {
        "translate": "Translate the following text from {from_lang} to {to_lang}:\n\n",
        "translate-without-from": "Translate the following text to {to_lang}:\n\n",
        "translate-en-to-zh": "将以下英文文本翻译成中文：\n\n",
        "translate-to-zh": "将以下文本翻译成中文：\n\n",
        "commit-summary": "Summarize the following commit messages:\n\n",
        "commit-summary-zh": "总结以下提交记录的关键信息：\n\n",
        "diff-analysis": "Analyze the following detailed diffs and summarize the key changes:\n\n",
        "diff-analysis-zh": "分析以下详细的代码差异，并总结出关键的更改内容：\n\n"
    }
    @abstractmethod
    async def generate(self, prompt: str, input: str) -> str:
        pass
    # 下面这些方法可能与Client交互，以完成更复杂的任务；它们包括了具体实现。
    async def translate(self, from_lang: Optional[str], to_lang: str, text: str) -> str:
        if "translate" not in self.prompts:
            raise NotImplementedError("Translate prompt is not defined.")
        if from_lang and f"translate-{from_lang}-to-{to_lang}" in self.prompts:
            prompt = self.prompts.get(f"translate-{from_lang}-to-{to_lang}", "")
        elif f"translate-to-{to_lang}" in self.prompts:
            prompt = self.prompts.get(f"translate-to-{to_lang}", "")
        elif from_lang:
            prompt = self.prompts.get("translate", "").format(from_lang=from_lang, to_lang=to_lang)
        else:
            prompt = self.prompts.get("translate-without-from", "").format(to_lang=to_lang)
        return await self.generate(prompt, text)
    async def summarize_repository_changes_since(self, client: GenericClient, owner: str, repo: str, since: datetime, branch: str = "main", diff_analysis: bool = False) -> str:
        """
        总结自指定时间以来的仓库更改内容。
        如果diff_analysis为True，则获取更详细的diff信息进行分析。
        """
        summary_prompt = self.prompts.get("commit-summary", "")
        if diff_analysis:
            commits_data = str(await client.get_commit_messages_since(owner, repo, since, contains_full_sha=True, branch=branch)).splitlines()
            commit_sha = ""
            parent_sha = ""
            analysis_prompt = self.prompts.get("diff-analysis", "")
            for commit in commits_data:
                commit = commit.strip()
                if commit.startswith("Commit "):
                    if len(parent_sha):
                        commit_sha = parent_sha
                    for i in range(7, len(commit) - 2):
                        if commit[i:i+3] == "by ":
                            parent_sha = commit[8:i]
                            break
                diff = await client.compare_two_commits(owner, repo, parent_sha, commit_sha) if len(parent_sha) and len(commit_sha) else ""
                extracted_diff = await self.generate(analysis_prompt, diff) if len(diff) else ""
                if extracted_diff:
                    commit = extracted_diff + "\n" + commit
            return await self.generate(summary_prompt, "\n".join(commits_data))
        else:
            commit_messages = await client.get_commit_messages_since(owner, repo, since, contains_full_sha=False, branch=branch)
            return await self.generate(summary_prompt, commit_messages)