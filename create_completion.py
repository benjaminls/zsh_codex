#!/usr/bin/env python3

import sys
import os
import re
import configparser
import argparse
import prompt_library

# Conditionally import OpenAI and Google Generative AI
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Get config dir from environment or default to ~/.config
CONFIG_DIR = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
OPENAI_API_KEYS_LOCATION = os.path.join(CONFIG_DIR, "openaiapirc")
GEMINI_API_KEYS_LOCATION = os.path.join(CONFIG_DIR, "geminiapirc")

# Allow users to pick the model they wish to run:
OPENAI_DEFAULT_MODEL = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")
GEMINI_DEFAULT_MODEL = os.getenv("GEMINI_DEFAULT_MODEL", "gemini-1.5-pro-latest")


def extract_paths(text: str):
    """
    Input text containing any number of paths and output a list of paths.

    Args:
        text (str): Text containing paths(s).

    Returns:
        (list[str]): List of strings of matched paths.
    """
    # regular expression patterns for unix-like and windows paths
    unix_path_pattern = r"(\.{1,2}/\S+|/\S+|\b\S+/\S+\b)"
    windows_path_pattern = r"[a-zA-Z]:\\(?:[^\\\s,]+\\?)*[^\\\s,]+"

    # combine patterns to search for both types of paths
    combined_pattern = f"{unix_path_pattern}|{windows_path_pattern}"

    # find all matches in the input string
    matches = re.findall(combined_pattern, text)

    # Check that all elements of
    if not all([[isinstance(p, str)] for p in matches]):
        print("[ WARNING ] Failed to extract paths in zsh_codex")
        return []

    return matches


def extract_valid_dirs(paths: list, cwd: str):
    """
    Take list of paths and output valid directories, not files.

    Args:
        paths (list): List of paths to be checked.
        cwd (str): Current working directory.

    Returns:
        (list): List of valid paths.
    """
    valid_dirs = []
    for path in paths:
        if os.path.isdir(os.path.join(cwd, path)):
            valid_dirs.append([path])

    return valid_dirs


def extract_valid_files(paths: list, cwd: str):
    """
    Take list of paths and output valid files, not directories.

    Args:
        paths (list): List of paths to be checked.
        cwd (str): Current working directory.

    Returns:
        (list): List of valid files.
    """
    valid_files = []
    for path in paths:
        if os.path.exists(os.path.join(cwd, path)) and not os.path.isdir(
            os.path.join(cwd, path)
        ):
            valid_files.append([path])

    return valid_files


def create_template_ini_file(api_type):
    """
    If the ini file does not exist create it and add the api_key placeholder
    """
    if api_type == "openai":
        file_path = OPENAI_API_KEYS_LOCATION
        content = "[openai]\nsecret_key=\napi_base=https://api.openai.com/v1\nmodel=gpt-4-turbo-preview\n"
        url = "https://platform.openai.com/api-keys"
    else:  # gemini
        file_path = GEMINI_API_KEYS_LOCATION
        content = "[gemini]\napi_key=\n"
        url = "Google AI Studio"

    if not os.path.isfile(file_path):
        with open(file_path, "w") as f:
            f.write(content)

        print(f"{api_type.capitalize()} API config file created at {file_path}")
        print("Please edit it and add your API key")
        print(f"If you do not yet have an API key, you can get it from: {url}")
        sys.exit(1)


def initialize_api(api_type):
    """
    Initialize the specified API
    """
    create_template_ini_file(api_type)
    config = configparser.ConfigParser()

    if api_type == "openai":
        config.read(OPENAI_API_KEYS_LOCATION)
        api_config = {k: v.strip("\"'") for k, v in config["openai"].items()}
        client = OpenAI(
            api_key=api_config["secret_key"],
            base_url=api_config.get("api_base", "https://api.openai.com/v1"),
            organization=api_config.get("organization"),
        )
        api_config.setdefault("model", api_config.get("model", OPENAI_DEFAULT_MODEL))
        return client, api_config
    else:  # gemini
        config.read(GEMINI_API_KEYS_LOCATION)
        api_config = {k: v.strip("\"'") for k, v in config["gemini"].items()}
        genai.configure(api_key=api_config["api_key"])
        api_config.setdefault("model", GEMINI_DEFAULT_MODEL)
        return genai, api_config


def get_completion(api_type, client, config, full_command, cwd):
    home = os.environ["HOME"]
    if api_type == "openai":
        with open(os.path.join(home, ".zsh_history"), "r", encoding="unicode_escape") as f:
            zsh_history = f.read()
            f.close()

        zsh_history = zsh_history.split("\n")[-1000:]
        zsh_history = "\n".join([item[15:] for item in zsh_history])

        send_messages = [
            {
                "role": "system",
                # "content": "You are a zsh shell expert, please help me complete the following command, you should only output the completed command, no need to include any other explanation. Do not put completed command in a code block.",
                "content": "You are a zsh shell expert, please help me complete the following command. Only output the completed command, no need for any other explanation. Do not put the completed command in a code block. The command should be a one-liner meant for the terminal. Shebangs like '#!/bin/bash' or '#!/bin/zsh' should NEVER be in your response. You are on MacOS. Avoid commands that are Linux exclusive, like 'apt' or 'yum'. After ",
            },
            {
                "role": "user",
                "content": full_command,
            },
            {
                "role": "system",
                "content": "Here is additional context to help with the command completion. You may find some of this information useful, but you are not required to use any of it unless it is relevant to the command.",
            },
            {
                "role": "system",
                "content": f"ls -larth: \n {os.listdir(cwd)}",
            },
            {
                "role": "system",
                "content": f"pwd: \n {cwd}",
            },
            {"role": "system", "content": f".zsh_history: \n {zsh_history}"},
        ]
        response = client.chat.completions.create(
            model=config["model"],
            messages=send_messages,
            temperature=float(config.get("temperature", 1.0)),
        )
        with open("send.txt", "w") as f:
            f.write(f"model = {config['model']}\n\n")
            f.write(f"messages = {send_messages}\n\n")
            f.close()
        with open("response.txt", "w") as f:
            f.write(f"{response.usage.__str__()}\n\n")
            f.write(f"{response.model.__str__()}\n\n")
            f.write(f"{response.choices.__str__()}\n\n")
            f.close()
        return response.choices[0].message.content
    else:  # gemini
        model = client.GenerativeModel(config["model"])
        chat = model.start_chat(history=[])
        # prompt = "You are a zsh shell expert, please help me complete the following command. Only output the completed command, no need for any other explanation. Do not put the completed command in a code block.\n\n" + full_command
        prompt = (
            "You are a zsh shell expert, please help me complete the following command. Only output the completed command, no need for any other explanation. Do not put the completed command in a code block. The command should be a one-liner meant for the terminal. Shebangs like '#!/bin/bash' or '#!/bin/zsh' should NEVER be in your response. You are on MacOS. Avoid reponses with potentially dangerous commands, like 'rm -rf *' or 'sudo' unless absolutely necessary. \n\n"
            + full_command
        )
        response = chat.send_message(prompt)
        return response.text


def main():
    parser = argparse.ArgumentParser(
        description="Generate command completions using AI."
    )
    parser.add_argument(
        "--api",
        choices=["openai", "gemini"],
        default="openai",
        help="Choose the API to use (default: openai)",
    )
    parser.add_argument(
        "cursor_position", type=int, help="Cursor position in the input buffer"
    )
    parser.add_argument("--cwd", default="", help="Current working directory.")
    args = parser.parse_args()

    if args.api == "openai" and OpenAI is None:
        print(
            "OpenAI library is not installed. Please install it using 'pip install openai'"
        )
        sys.exit(1)
    elif args.api == "gemini" and genai is None:
        print(
            "Google Generative AI library is not installed. Please install it using 'pip install google-generativeai'"
        )
        sys.exit(1)

    client, config = initialize_api(args.api)

    # Read the input prompt from stdin.
    buffer = sys.stdin.read()
    zsh_prefix = "#!/bin/zsh\n\n"
    buffer_prefix = buffer[: args.cursor_position]
    buffer_suffix = buffer[args.cursor_position :]
    full_command = zsh_prefix + buffer_prefix + buffer_suffix

    completion = get_completion(args.api, client, config, full_command, args.cwd)

    if completion.startswith(zsh_prefix):
        completion = completion[len(zsh_prefix) :]

    line_prefix = buffer_prefix.rsplit("\n", 1)[-1]
    # Handle all the different ways the command can be returned
    for prefix in [buffer_prefix, line_prefix]:
        if completion.startswith(prefix):
            completion = completion[len(prefix) :]
            break

    if buffer_suffix and completion.endswith(buffer_suffix):
        completion = completion[: -len(buffer_suffix)]

    completion = completion.strip("\n")
    # if line_prefix.strip().startswith("#"): # for inline #Comment replace
    #     completion = "\n" + completion

    sys.stdout.write(completion)


if __name__ == "__main__":
    main()
