from typing import Optional, Dict, Callable, Union, Tuple
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

CommandDictType = Dict[str, Union[None, Callable[..., Optional[str]], 'CommandDictType']]
class CommandParser:
    command_dict: CommandDictType
    def __init__(self, command_dict: CommandDictType) -> None:
        self.command_dict = command_dict

    def parse(self, prompt: str) -> Optional[str]:
        current_level = self.command_dict
        commands = prompt.split(" ")
        cmd = ""
        is_first = True
        while True:
            if len(commands) == 0:
                return None
            subcmd = commands.pop(0)
            cmd += f" {subcmd}"
            if current_level and subcmd in current_level:
                next_level = current_level[subcmd]
                if subcmd == "help" and is_first:
                    help_text = "Available commands:\n"
                    for key in current_level.keys():
                        help_text += f"  {key}\n"
                    return help_text
                if callable(next_level):
                    # 位置参数传递给函数
                    if all((c == "" or c[0] != "-") and (len(c) < 2 or c[1] != "-") for c in commands):
                        return next_level(*commands)
                    # 关键词参数传递给函数
                    elif all((c.startswith("--") and "=" in c) for c in commands):
                        return next_level(**{c.lstrip("--").split("=")[0]: c.lstrip("--").split("=")[1] for c in commands})
                else:
                    current_level = next_level
            else:
                raise SyntaxError(f"Unknown command: {cmd.strip()}")
            is_first = False
    def get_completer(self) -> NestedCompleter:
        def build_completer(command_dict: CommandDictType) -> NestedCompleter:
            completer_dict = {}
            for key, value in command_dict.items():
                if callable(value) or value is None:
                    completer_dict[key] = None
                else:
                    completer_dict[key] = build_completer(value)
            return NestedCompleter.from_nested_dict(completer_dict)
        return build_completer(self.command_dict)
class CommandPrompt:
    session: PromptSession
    completer: NestedCompleter
    parser: CommandParser
    scheduler: AsyncIOScheduler
    def __init__(self, parser: CommandParser) -> None:
        self.session = PromptSession()
        self.parser = parser
        self.completer = self.parser.get_completer()

    async def run(self):
        while True:
            prompt = await self.session.prompt_async(">", completer=self.completer)
            try:
                result = self.parser.parse(prompt)
                if result == "exit":
                    print("Exiting...")
                    break
                if result is not None:
                    print(result)
            except SyntaxError as e:
                logging.error(f"Syntax Error: {e}")
            except Exception as e:
                logging.error(f"Error: {e}")