import sys
import os
from vc_firm.crew import VcFirmCrew

def run():
    # 1. Define the path to your new text file
    file_path = 'startup_pitch.txt'

    # 2. Check if the file exists before running
    if not os.path.exists(file_path):
        print(f"❌ ERROR: Could not find '{file_path}'. Please create it and paste a pitch inside.")
        sys.exit(1)

    # 3. Read the contents of the file seamlessly
    with open(file_path, 'r', encoding='utf-8') as file:
        pitch_text = file.read()
    
    # 4. Feed the text from the file into the AI agents
    inputs = {
        'pitch_data': pitch_text
    }
    
    print("Reading pitch file... Starting the 7-Agent VC Firm...")
    VcFirmCrew().crew().kickoff(inputs=inputs)

if __name__ == '__main__':
    run()