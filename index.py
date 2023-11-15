import speech_recognition as sr
from gtts import gTTS
from tempfile import TemporaryFile
from playsound import playsound
import os, sys, argparse
import tempfile
import requests
from dotenv import load_dotenv
from colorama import init, Fore
import service.tts as tts
import service.stt as stt
import threading
import concurrent.futures
import json
import utils

load_dotenv()

init()


def cli_argument():
    parser = argparse.ArgumentParser(description="Which language do you use for recording?")
    parser.add_argument("-l", "--language", dest="language", type=str,
                        help="Language for recording", default="en-US",
                        required=True, nargs="+")
    argument = parser.parse_args()
    if not argument.language:
        print(f"{Fore.RED}[-] Please specify the a language for recording."
              " Use --help to see usage.")
        sys.exit()
    return argument

args = cli_argument()
language = "".join(args.language)


while(1):
    text = stt.record_text(language)
    origin_url = os.getenv("ORIGIN_URL", "http://localhost:8000")
    url = f'{origin_url}/api/v1/chatgpt/ask-for-tts'
    

    if text is not None:
        # Define your tasks
        def task1(task1_completed, task2_completed):
            with open('fake_res.json') as f:
                fake_res = json.load(f)
                fake_text = utils.get_random_value(fake_res[language])
                print(fake_text)
            tts.text_to_speech_OpenAI(fake_text, 0.8)
            task1_completed.set()  # Indicate that task1 is completed

        def task2(task1_completed, task2_completed):
            headers = {'Content-Type': 'application/json'}
            payload = {
                'data': {
                    'content': text,
                    'guildId': os.environ['GUILD_ID']
                },
                'maxTokenEachScript': 80,
                'curUser': {
                    'globalName': os.environ['USER_GLOBALNAME'],
                    'id': os.environ['USER_ID'],
                }
            }

            response = requests.post(url, headers=headers, json=payload)
            task2_completed.set()  # Indicate that task2 is completed

            # Wait for task1 to finish if it's still running
            if not task1_completed.is_set():
                task1_completed.wait()

            if response.status_code == 200:
                print(f"{Fore.BLACK}==========>", response.json()['data'])
                tts.text_to_speech_OpenAI(response.json()['data'], 1)
            else:
                print("Oops, no pizza. Let's try again!")

        task1_completed = threading.Event()
        task2_completed = threading.Event()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future1 = executor.submit(task1, task1_completed, task2_completed)
            future2 = executor.submit(task2, task1_completed, task2_completed)

            # If task2 finishes first, cancel task1
            if task2_completed.is_set() and not task1_completed.is_set():
                executor._threads.clear()
                concurrent.futures.thread._threads_queues.clear()