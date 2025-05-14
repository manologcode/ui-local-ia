import requests
import os

PODCAST_URL_BASE = os.getenv("PODCAST_URL_BASE", "http://192.168.1.69:5002")


def create_episode(token: str, podcast_id: int, title: str, description: str, audio_filepath: str, duration: str = None):
    """
    Creates a new episode for a given podcast by sending a POST request to the API.

    Args:
        token: The API token for authentication.
        podcast_id: The ID of the podcast the episode belongs to.
        title: The title of the episode.
        description: A brief description of the episode.
        audio_filepath: The path to the episode's audio file.
        duration: The duration of the episode in HH:MM:SS format (optional).

    Returns:
        A dictionary containing the created episode data if successful, None otherwise.
    """
    url = f"{PODCAST_URL_BASE}/podcasts/{podcast_id}/episodes/"
    files = {'audio_file': open(audio_filepath, 'rb')}
    data = {
        'title': title,
        'description': description,
    }
    if duration:
        data['duration'] = duration

    headers = {
        'Authorization': f'Bearer {token}'
    }

    try:
        response = requests.post(url, files=files, data=data, headers=headers)
        response.raise_for_status() # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error creating episode: {e}")
        return None
    finally:
        files['audio_file'].close() # Close the file after sending
