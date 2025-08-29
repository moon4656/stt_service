import requests
import time
import os


class TiroAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.tiro-ooo.dev/v1/external/voice-file"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def create_job(self, transcript_locale_hints=None, translation_locales=None):
        payload = {}
        
        if transcript_locale_hints:
            payload["transcriptLocaleHints"] = transcript_locale_hints[:1]
            
        if translation_locales:
            payload["translationLocales"] = translation_locales[:5]
        
        response = requests.post(
            f"{self.base_url}/jobs",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def upload_file(self, upload_uri, file_path):
        with open(file_path, 'rb') as file:
            response = requests.put(upload_uri, data=file)
            response.raise_for_status()
        
        print(f"File uploaded successfully: {file_path}")
    
    def notify_upload_complete(self, job_id):
        response = requests.put(
            f"{self.base_url}/jobs/{job_id}/upload-complete",
            headers=self.headers
        )
        response.raise_for_status()
        print(f"Upload complete notification sent for job: {job_id}")
    
    def poll_job_status(self, job_id, max_wait_time=600):
        interval = 1
        max_interval = 10
        elapsed_time = 0
        
        success_statuses = ["TRANSLATION_COMPLETED"] # until translation
        # success_statuses = ["TRANSCRIPT_COMPLETED"]
        failure_statuses = ["FAILED"]
        
        while elapsed_time < max_wait_time:
            response = requests.get(
                f"{self.base_url}/jobs/{job_id}",
                headers=self.headers
            )
            response.raise_for_status()
            
            job_data = response.json()
            status = job_data.get("status")
            
            print(f"Job {job_id} status: {status} (elapsed: {elapsed_time}s)")
            
            if status in success_statuses:
                print(f"Job completed successfully with status: {status}")
                return status
            elif status in failure_statuses:
                print(f"Job failed with status: {status}")
                return status
            
            time.sleep(interval)
            elapsed_time += interval
            
            # Exponential backoff with cap
            interval = min(interval * 2, max_interval)
        
        print(f"Polling timeout after {max_wait_time} seconds")
        return "TIMEOUT"
    
    def get_transcript(self, job_id):
        response = requests.get(
            f"{self.base_url}/jobs/{job_id}/transcript",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_translations(self, job_id):
        response = requests.get(
            f"{self.base_url}/jobs/{job_id}/translations",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def process_audio_file(self, file_path, transcript_locale_hints=None, translation_locales=None):
        """
        Complete workflow: create job, upload file, notify, poll, and get results
        
        Args:
            file_path (str): Path to audio file
            transcript_locale_hints (list): Optional locale hints
            translation_locales (list): Optional translation locales
            
        Returns:
            dict: Complete results including transcript and translations
        """
        print(f"Starting audio processing for: {file_path}")
        
        # Step 1: Create job
        job_response = self.create_job(transcript_locale_hints, translation_locales)
        job_id = job_response["id"]
        upload_uri = job_response["uploadUri"]
        
        print(f"Job created: {job_id}")
        
        # Step 2: Upload file
        self.upload_file(upload_uri, file_path)
        
        # Step 3: Notify upload complete
        self.notify_upload_complete(job_id)
        
        # Step 4: Poll for completion
        final_status = self.poll_job_status(job_id)
        
        if final_status not in ["TRANSCRIPT_COMPLETED", "TRANSLATION_COMPLETED"]:
            return {"error": f"Job failed with status: {final_status}"}
        
        # Step 5: Get results
        results = {}
        
        try:
            transcript = self.get_transcript(job_id)
            results["transcript"] = transcript
        except requests.exceptions.RequestException as e:
            print(f"Error getting transcript: {e}")
        
        if translation_locales:
            try:
                translations = self.get_translations(job_id)
                results["translations"] = translations
            except requests.exceptions.RequestException as e:
                print(f"Error getting translations: {e}")
        
        return results


def main():
    api_key = "00ZlNnjn3ugPY.IJtCXZKio6W34GoEJdMJnsGDnXtVgCQabhsD7DVE6h0"  # Replace with your actual API key
    tiro = TiroAPI(api_key)
    
    # Example audio file path
    # audio_file = "short-audio.mp4"  # Replace with actual file path
    audio_file = "meeting_20250809_110851_full.mp3"  # Replace with actual file path
    # audio_file = "path/to/your/audio/file.wav"  # Replace with actual file path

    if not os.path.exists(audio_file):
        print(f"Audio file not found: {audio_file}")
        print("Please update the 'audio_file' variable with a valid file path")
        return
    
    try:
        results = tiro.process_audio_file(
            file_path=audio_file,
            transcript_locale_hints=["ko_KR"]  # Korean transcript
            # translation_locales=["en_US"]       # English translation
        )
        
        if "error" in results:
            print(f"Processing failed: {results['error']}")
        else:
            print("Processing completed successfully!")
            
            # Print transcript
            if "transcript" in results:
                transcript_data = results["transcript"]
                print(f"\nTranscript (Status: {transcript_data.get('status')}):")
                print(transcript_data.get("text", "No text available"))
            
            # Print translations
            if "translations" in results:
                translations_data = results["translations"]
                print(f"\nTranslations:")
                for translation in translations_data:
                    locale = translation.get("locale")
                    status = translation.get("status")
                    text = translation.get("text", "No text available")
                    print(f"  {locale} (Status: {status}): {text}")
    
    except Exception as e:
        print(f"Error processing audio: {e}")


if __name__ == "__main__":
    main()