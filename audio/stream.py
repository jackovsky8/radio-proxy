import requests
from pydub import AudioSegment
from io import BytesIO
from datetime import datetime
from mutagen.mp3 import MP3, HeaderNotFoundError
from os import listdir, remove
from pathlib import Path
from urllib import request
from functools import reduce
from ssl import create_default_context, CERT_NONE
from threading import Thread

DATA_DIR: Path = Path(__file__).parent.parent.joinpath('data')

class Stream:
    def __init__(self, url: str, stream_id: str):
        self.url = url
        self.stream_id = stream_id
        self.last_accessed = datetime.now()
        self.thread = None
        self.record = True

    def start_recording(self):
        """
        Start recording the stream
        """
        if self.thread is None:
            self.thread = Thread(target=self.save_stream_as_files)
            self.thread.start()
            self.record = True
    
    def stop_recording(self):
        """
        Stop recording the stream
        """
        if self.thread is not None:
            self.record = False
            self.thread.join()
            self.thread = None
    
    def delete_files_of_stream(self) -> None:
      """
      Delete all files with the given prefix
      """
      for file_name in listdir(DATA_DIR):
          if file_name.startswith(prefix):
              remove(DATA_DIR.joinpath(file_name))

    def save_stream_as_files(self) -> None:
        """
        Save the stream as files
        """
        # Send an HTTP GET request to fetch the MP3 stream with SSL certificate verification disabled
        response = requests.get(self.url, stream=True, verify=False)

        # Get the bitrate from the response header
        try:
          # TODO more resilient way to get bitrate
          bitrate = int(response.headers['icy-br'])
        except ValueError:
          bitrate = 128
        
        print(f"Bitrate: {bitrate}")

        # Check if the request was successful (status code 200)
        if response.status_code == 200:

            # Create a new file
            output_filename = f"{self.stream_id}_{self.get_date_and_time_as_string()}.mp3"

            # Iterate through the response content in chunks and write them to the output file
            for chunk in response.iter_content(chunk_size=1024*bitrate):
                # Stop recording if the thread was stopped
                if not self.record:
                    break
                # If a chunk is available save it to the file
                if chunk:
                    if file_contains_title(BytesIO(chunk)) or file_is_larger_than(DATA_DIR.joinpath(output_filename), 1024*128):
                        # Create a new file
                        print(
                            f"Saved the MP3 from the internet radio to '{output_filename}'")
                        output_filename = f"{self.stream_id}_{self.get_date_and_time_as_string()}.mp3"

                    # Add chunk to file
                    with open(DATA_DIR.joinpath(output_filename), 'ab') as output_file:
                        output_file.write(chunk)

        else:
            print(
                f"Failed to fetch MP3 stream. Status code: {response.status_code}")


    def get_date_and_time_as_string(self):
        # Get the current date and time
        now = datetime.now()

        # Format the date and time as a string
        return now.strftime("%d_%m_%Y_%H_%M_%S")


def file_contains_title(file):
    try:
        mp3 = MP3(file)
        if mp3.tags is not None:
          print(mp3.tags)
        # Check if Metadata exists
        metadata = mp3.get('title', ['Unknown'])[0]
        # Then we save the file
        if metadata != 'Unknown':
            return True
    except HeaderNotFoundError:
        print("HeaderNotFoundError")
        pass

    return False

def file_is_larger_than(path: Path, size):
    try:
      return path.stat().st_size > size
    except FileNotFoundError:
        return False


# def get_n_bytes(url, size):
#     req = request.Request(url)
#     req.headers['Range'] = 'bytes=%s-%s' % (0, size-1)
#     ctx = create_default_context()
#     ctx.check_hostname = False
#     ctx.verify_mode = CERT_NONE
#     response = request.urlopen(req, context=ctx)
#     return response.read()


# def retrieve_metadata(prefix: str, url: str) -> None:
#     data = get_n_bytes(url, 10)
#     if data[0:3] != 'ID3':
#         raise Exception('ID3 not in front of mp3 file')

#     size_encoded = bytearray(data[-4:])
#     size = reduce(lambda a, b: a*128+b, size_encoded, 0)

#     header = BytesIO()
#     # mutagen needs one full frame in order to function. Add max frame size
#     data = get_n_bytes(url, size+2881)
#     header.write(data)
#     header.seek(0)
#     f = MP3(header)

#     if f.tags and 'APIC:' in f.tags.keys():
#         artwork = f.tags['APIC:'].data
#         with open('image.jpg', 'wb') as img:
#             img.write(artwork)


if __name__ == '__main__':    
    prefix = "ankerherz"
    url = 'https://radio.ankerherz.de/radioankerherz.mp3'

    # prefix = "fm4"
    # url = 'https://orf-live.ors-shoutcast.at/fm4-q1a'

    # prefix = "oe1"
    # url = 'https://orf-live.ors-shoutcast.at/oe1-q1a'

    # prefix = "oe3"
    # url = 'https://orf-live.ors-shoutcast.at/oe3-q1a'

    stream = Stream(url, prefix)
    stream.delete_files_of_stream()
    stream.start_recording()
    from time import sleep
    sleep(300)
    stream.stop_recording()

