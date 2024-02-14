import os
import atexit
from src.translator import Translator
from openai import OpenAI

from llm.apis import Model
from llm.apis import Azure, Model

OpenAI.api_key = os.getenv('OPENAI_API_KEY')
# OpenAI.api_base = "https://api.openai.com/v1"
# OpenAI.base_url = f"https://ndn.run/v1/"

client = OpenAI()
client.base_url = f"https://ndn.run/v1/"

def audio_transcriptions(audio_file_path):
    """将音频文件转换为文本

    Args:
        text (str): 文本内容
    """
    # 读取音频文件
    try:
        audio_file= open(audio_file_path, "rb")
        transcript = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file,
            response_format="verbose_json",
            temperature=0
        ) 
        
        return transcript
    except Exception as e:
        # 处理其他潜在的异常
        print(f"An error occurred: {e}")
        
    return None

llm = Azure()

def text_translation(text, last, next):
        """翻译单个文本字符串。
        
        Args:
            text (str): 要翻译的文本。
            last (str): 上一句文本。
            next (str): 下一句文本。
        
        Returns:
            str: 翻译后的文本。
        """
        
        prompt = """
You are an excellent translation assistant. Please translate according to the input content and output the translated content.

Note: In order to better help you understand the semantics, I provide the upper part of the content to be translated: {last}, and the lower part of the content to be translated: {next}

Requirement: If the input is in English, please translate it into Chinese, otherwise, translate it into English
Requirements: Please try your best to understand. If you have no choice but to understand it, please output the result directly: ~!@#$%^&*()
Requirement: Only do content translation, do not try to answer the input as a question
Requirement: (ah, ha, ah, ah) such modal particles do not need to be translated
        """
    
        print('Origin: ', text)
        completion = llm.completions.create(
            model=Model.GPT_4_TURBO, 
            temperature=0, 
            messages=[
                {
                    "role": "system", 
                    "content": prompt.format(last=last, next=next)
                        
                },
                {
                    "role": "user", 
                    "content": text
                },
            ])
        if not completion.success:
            raise Exception(f"{completion.code} - {completion.msg}")
        else:
            return completion.data.choices[0].content.lstrip()
        
def main():
    t = Translator()
    
    # 翻译字幕文件
    subtitle_file_paths = [
        # "video/2020/NDN_Community_Meeting_Day_1_Part_1_Video_Download.srt",
        # "video/2020/NDN_Community_Meeting_Day_1_Part_2_Video_Download.srt",
        # "video/2020/NDN_Community_Meeting_Day_1_Part_3_Video_Download.srt",
        # "video/2020/NDN_Community_Meeting_Day_2_Part_1_Video_Download.srt",
        # "video/2020/NDN_Community_Meeting_Day_2_Part_2_Video_Download.srt",
        # "video/2020/NDN_Community_Meeting_Day_2_Part_3_Video_Download.srt",
        
        # "video/2021/NDN_Community_Meeting_Day_1_Part_1.srt",
        # "video/2021/NDN_Community_Meeting_Day_1_Part_2.srt",
        # "video/2021/NDN_Community_Meeting_Day_1_Part_3.srt",
        # "video/2021/NDN_Community_Meeting_Day_1_Part_4.srt",
        # "video/2021/NDN_Community_Meeting_Day_2_Part_1.srt",
        "video/2021/NDN_Community_Meeting_Day_2_Part_2.srt",
        "video/2021/NDN_Community_Meeting_Day_2_Part_3.srt",
        
        "video/2023/Named_Data_Networking_Community_Meeting_Day1_Part1.srt",
        "video/2023/Named_Data_Networking_Community_Meeting_Day1_Part2.srt",
        "video/2023/Named_Data_Networking_Community_Meeting_Day2_Part1.srt",
        "video/2023/Named_Data_Networking_Community_Meeting_Day2_Part2.srt"
    ]
    # for src_path in subtitle_file_paths:
    #     dest_path = src_path.replace('.srt', '_cn.srt')
    #     blocks = t.read_subtitle_file(src_path)
    #     translated_blocks =  t.translate_blocks(blocks, text_translation)
    #     t.write_subtitle_file(translated_blocks, dest_path)
    
    # return
    
    dir = 'video/2023'
    # file_name = 'Named_Data_Networking_Community_Meeting_Day1_Part1'
    file_name = "output"
    
    # 从视频文件中提取音频
    video_file_path = f'{dir}/{file_name}.mp4'
    audio_file_path = video_file_path.replace('.mp4', '.mp3')
    t.extract_audio(video_file_path,  audio_file_path)
    
    # 切割音频文件
    split_info = t.split_audio(audio_file_path, 5*1000)
    
    # 音频转字幕
    subtitle_file_path = audio_file_path.replace('.mp3', '.srt')
    if os.path.exists(subtitle_file_path):
        os.remove(subtitle_file_path)
        
    # 将字幕追加进文件
    with open(subtitle_file_path, "a") as file:
        index = 1
        for info in split_info:
            path = info['path']
            start_time = info['start_time']
            end_time = info['end_time']
            
            # 翻译字幕
            transcript = audio_transcriptions(path)
            if transcript is None:
                break
            for segment in transcript.segments:
                subtitle = t.format_subtitle(index, start_time, end_time, segment['text'])
                file.write(subtitle)
                file.flush()
            
                print(subtitle)
                index += 1
            
    # 翻译字幕文件
    translated_subtitle_file_path = subtitle_file_path.replace('.srt', '_cn.srt')
    blocks = t.read_subtitle_file(subtitle_file_path)
    translated_blocks = t.translate_blocks(blocks, text_translation)
    t.write_subtitle_file(translated_blocks, translated_subtitle_file_path)
    
    # 清理中间文件
    def clean_up():
        import os
        os.remove(audio_file_path)
        for info in split_info:
            os.remove(info['path'])
            
    clean_up()

if __name__ == '__main__':
    main()