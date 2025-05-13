# Bedrock Agent Chat Application

A simple chat application that allows you to interact with Amazon Bedrock Agents through a responsive web interface.

## Features

- Interactive chat interface with Amazon Bedrock Agents
- Agent selector dropdown in the settings menu
- Display of agent rationale for transparency
- Responsive UI for both desktop and mobile devices
- Light/dark mode toggle for user preference
- Real-time agent responses

## Prerequisites

- Python 3.8+
- AWS account with access to Amazon Bedrock
- AWS credentials with appropriate permissions for Bedrock Agent

## Installation

1. Clone this repository:
```
git clone https://github.com/yourusername/bedrock-agent-app.git
cd bedrock-agent-app
```

2. Install the required dependencies:
```
pip install -r requirements.txt
```

3. Set up your AWS credentials:
   - Copy the `.env.example` file to `.env`
   - Fill in your AWS credentials in the `.env` file

## Usage

1. Start the application:
```
streamlit run app.py
```

2. Open your web browser and navigate to the URL displayed in the terminal (typically http://localhost:8501)

3. Select a Bedrock Agent from the dropdown in the sidebar

4. Start chatting with your selected agent!

## Configuration

- The application uses the AWS credentials specified in the `.env` file
- By default, the application connects to the us-east-1 region
- You can toggle the display of agent rationale in the settings sidebar

## Customization

- Modify the CSS in the `apply_custom_css()` function to change the appearance
- Adjust the agent invocation parameters in the `invoke_agent()` function

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [Amazon Bedrock](https://aws.amazon.com/bedrock/)