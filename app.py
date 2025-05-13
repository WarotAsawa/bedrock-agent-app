import streamlit as st
import boto3
import json
import os, time
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="Bedrock Agent Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_id" not in st.session_state:
    st.session_state.agent_id = None
if "agent_name" not in st.session_state:
    st.session_state.agent_name = None
if "agent_alias_id" not in st.session_state:
    st.session_state.agent_alias_id = None
if "agents_data" not in st.session_state:
    st.session_state.agents_data = {}
if "selected_agent_aliases" not in st.session_state:
    st.session_state.selected_agent_aliases = {}

def initialize_bedrock_clients():
    """Initialize and return the Bedrock clients."""
    # Client for agent management operations
    bedrock_agent = boto3.client(
        service_name='bedrock-agent',
        region_name='us-east-1',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    # Client for agent runtime operations
    bedrock_agent_runtime = boto3.client(
        service_name='bedrock-agent-runtime',
        region_name='us-east-1',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    return bedrock_agent, bedrock_agent_runtime

def get_agents_data():
    """Get all available Bedrock Agents with their aliases."""
    try:
        bedrock_agent, _ = initialize_bedrock_clients()
        
        # Get all agents
        response = bedrock_agent.list_agents()
        agents = response.get('agentSummaries', [])
        
        agents_data = {}
        
        # For each agent, get its aliases and details
        for agent in agents:
            agent_id = agent['agentId']
            agent_name = agent['agentName']
            
            # Get detailed agent information to check if multi-agent collaboration is enabled
            try:
                agent_details = bedrock_agent.get_agent(
                    agentId=agent_id
                )
                #print (agent_details['agent']['agentCollaboration'])
                # Check if multi-agent collaboration is enabled
                is_supervisor = True
                if 'agentCollaboration' in agent_details['agent']:
                    if agent_details['agent']['agentCollaboration'] == 'DISABLED':
                        is_supervisor = False
            
            except Exception as e:
                # If we can't get details, assume it's not a supervisor
                is_supervisor = False
                st.warning(f"Could not check multi-agent status for {agent_name}: {str(e)}")
            
            # Store basic agent info
            agents_data[agent_id] = {
                'name': agent_name,
                'is_supervisor': is_supervisor,
                'aliases': {}
            }
            
            try:
                # Get aliases for this agent
                aliases_response = bedrock_agent.list_agent_aliases(
                    agentId=agent_id,
                    maxResults=10
                )
                
                aliases = aliases_response.get('agentAliasSummaries', [])
                
                # Store aliases
                if aliases:
                    for alias in aliases:
                        alias_id = alias['agentAliasId']
                        alias_name = alias['agentAliasName']
                        agents_data[agent_id]['aliases'][alias_id] = alias_name
                
            except Exception as e:
                st.warning(f"Could not fetch aliases for agent {agent_name}: {str(e)}")
        
        return agents_data
    except Exception as e:
        st.error(f"Error listing agents: {str(e)}")
        return {}

def invoke_agent(agent_id, agent_alias_id, prompt):
    """Invoke a Bedrock Agent with the given prompt."""
    if "metrics" not in st.session_state:
        st.session_state.metrics = {}
    # Start timing and capture input output tokens
    startTime = time.time()
    inputTokens = 0
    outputTokens = 0
    try:
        _, client = initialize_bedrock_clients()
        
        # Invoke the agent
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=f"session-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            inputText=prompt,
            enableTrace=True
        )
        
        # Process the response
        full_response = ""
        #trace_data = None
        
        # Check if completion is in the response
        if 'completion' in response:
            response_stream = response.get('completion')
            #print(response_stream)
            
            # Handle streaming response
            for event in response_stream:
                if 'trace' in event:
                    try:
                        if isinstance(event['trace'], dict) and 'bytes' in event['trace']:
                            trace_bytes = event['trace']['bytes']
                            if isinstance(trace_bytes, bytes):
                                trace_data = json.loads(trace_bytes.decode('utf-8'))
                            elif isinstance(trace_bytes, str):
                                trace_data = json.loads(trace_bytes)
                        else:
                            trace_data = event['trace']
                        if 'trace' in event['trace']: 
                            eventTrace = event['trace']['trace']
                            # Check all input output tokens
                            traceTypes = ['postProcessingTrace','orchestrationTrace', 'preProcessingTrace','routingClassifierTrace']
                            for traceType in traceTypes:
                                if traceType in eventTrace:
                                    if 'modelInvocationOutput' in eventTrace[traceType]:
                                        inputTokens = inputTokens + eventTrace[traceType]['modelInvocationOutput']['metadata']['usage']['inputTokens']
                                        outputTokens = outputTokens + eventTrace[traceType]['modelInvocationOutput']['metadata']['usage']['outputTokens']
                            #if 'orchestrationTrace' in eventTrace:
                                    if 'rationale' in eventTrace[traceType] and st.session_state.show_rationale == True:
                                        print('============================================================\n' + str(eventTrace[traceType]))
                                        starterText = "  \n 💭 "
                                        full_response += starterText
                                        yield starterText
                                        rationaleText = str(eventTrace[traceType]['rationale']['text'])
                                        full_response += rationaleText
                                        for word in rationaleText.split(" "):
                                                yield word + " "
                                                time.sleep(0.02)
                                    elif 'observation' in eventTrace[traceType]:
                                        print('============================================================\n' + str(eventTrace[traceType]))
                                        time.sleep(0.5)
                                        if 'finalResponse' in eventTrace[traceType]['observation']:
                                            starterText = "  \n   \n##### 💬 "
                                            full_response += starterText
                                            yield starterText
                                            observationText = str(eventTrace[traceType]['observation']['finalResponse']['text'])
                                            full_response += observationText
                                            for word in observationText.split(" "):
                                                yield word + " "
                                                time.sleep(0.02)
                    except Exception as e:
                        errorMessage = "⛔ Could not parse trace data:: "+ str(e)
                        for word in errorMessage.split(" "):
                            yield word + " "
                            time.sleep(0.02)    
            # Sum token and latency
            endTime =  time.time()
            elapsed_time_ms = (endTime - startTime) * 1000;
            st.session_state.metrics = {'latency': elapsed_time_ms, 'inputTokens': inputTokens, 'outputTokens': outputTokens}
        else:
            #trace_data = response.get('trace', {})
            errorMessage = '⛔ No Response Text Available. Please try again later!!!'
            for word in errorMessage.split(" "):
                yield word + " "
                time.sleep(0.02)    

    except Exception as e:
        errorMessage = "⛔ Error invoking agent: "+ str(e)
        for word in errorMessage.split(" "):
            yield word + " "
            time.sleep(0.02) 

# Add responsive design CSS
st.markdown("""
<style>
/* Responsive design */
@media (max-width: 768px) {
    .main .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
        padding-top: 1rem;
    }
}
</style>
""", unsafe_allow_html=True)

# Fetch agents data if not already in session state
if not st.session_state.agents_data:
    st.session_state.agents_data = get_agents_data()

# Sidebar for settings
with st.sidebar:
    st.title("Settings")
    
    # Agent selection
    st.subheader("Bedrock Agent")
    
    if st.session_state.agents_data:
        # Create a list of agent names for the dropdown with appropriate emoji
        agent_options = {}
        for agent_id, data in st.session_state.agents_data.items():
            # Add emoji based on whether it's a supervisor agent (multi-agent enabled)
            emoji = "👩‍✈️" if data['is_supervisor'] else "👨‍💼"
            display_name = f"{emoji} {data['name']} ({agent_id})"
            agent_options[display_name] = agent_id
        
        # Agent dropdown
        agent_selection = st.selectbox(
            "Select an agent:",
            options=list(agent_options.keys()),
            index=0 if agent_options else None,
            key="agent_selection"
        )
        
        if agent_selection:
            # Get the selected agent ID
            selected_agent_id = agent_options[agent_selection]
            
            # Update session state
            st.session_state.agent_id = selected_agent_id
            st.session_state.agent_name = st.session_state.agents_data[selected_agent_id]['name']
            
            # Get aliases for the selected agent
            aliases = st.session_state.agents_data[selected_agent_id]['aliases']
            
            if aliases:
                # Create a list of alias names for the dropdown
                alias_options = {f"{alias_name} ({alias_id})": alias_id 
                                for alias_id, alias_name in aliases.items()}
                
                # Alias dropdown
                st.subheader("Agent Alias")
                alias_selection = st.selectbox(
                    "Select an alias:",
                    options=list(alias_options.keys()),
                    index=0 if alias_options else None,
                    key="alias_selection"
                )
                
                if alias_selection:
                    # Get the selected alias ID
                    selected_alias_id = alias_options[alias_selection]
                    
                    # Update session state
                    st.session_state.agent_alias_id = selected_alias_id
                    
                    # Show agent type in the success message
                    agent_type = "Multi-Agent Supervisor" if st.session_state.agents_data[selected_agent_id]['is_supervisor'] else "Standard Agent"
                    st.success(f"Selected {agent_type}: {st.session_state.agent_name}")
                    st.success(f"Selected alias: {aliases[selected_alias_id]}")
            else:
                st.warning("No aliases available for this agent. Please select another agent.")
                st.session_state.agent_alias_id = None
    else:
        st.warning("No agents found. Please check your AWS credentials and permissions.")
    
    st.divider()
    
    # Display rationale toggle
    st.subheader("Display Options")
    st.session_state.show_rationale = st.checkbox("Show agent rationale", value=True)
    
    st.divider()
    
    # About section
    st.subheader("About")
    st.markdown("""
    This application allows you to chat with Amazon Bedrock Agents.
    
    Built with:
    - Streamlit
    - AWS Bedrock
    - Python
    """)
    
    # Note about theme toggle
    st.divider()
    st.caption("💡 Use Streamlit's native theme toggle in the top-right menu ⋮")

# Main chat interface
st.image('./img/bedrock.svg')
st.title("Bedrock Agent Chat")

# Display chat messages using Streamlit's native chat elements

for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message("user", avatar="🦖"):
            st.write(message["content"])
    else:
        with st.chat_message("assistant", avatar="🤖"):
            helpMessage = "No invoke metrics available"
            if 'metrics' in message:
                invokeMetrics = message["metrics"]
                helpMessage = f"*Invoke Latency: {str(invokeMetrics['latency'])}ms, Input Tokens: {str(invokeMetrics['inputTokens'])}, OutputTokens: {str(invokeMetrics['outputTokens'])}*"
            st.markdown(message["content"], help = helpMessage)
            
            # Display rationale in an expander if available and enabled
            # if "rationale" in message and st.session_state.show_rationale and message["rationale"] != "No rationale available":
            #     with st.expander("Agent Rationale"):
            #         st.code(message["rationale"], language="json")

# Chat input
if st.session_state.agent_id and st.session_state.agent_alias_id:
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Display user message
        with st.chat_message("user", avatar="🦖"):
            st.write(user_input)
        
        # Display "Agent is thinking..." message
        with st.chat_message("assistant", avatar="🤖"):
            #with st.spinner("Agent is thinking..."):
            response = invoke_agent(
                st.session_state.agent_id, 
                st.session_state.agent_alias_id, 
                user_input
            )
            
            writestream = st.write_stream(response)
            invokeMetrics = json.loads(json.dumps(st.session_state.metrics))
            st.write(f"*Invoke Latency: {str(invokeMetrics['latency'])}ms, Input Tokens: {str(invokeMetrics['inputTokens'])}, OutputTokens: {str(invokeMetrics['outputTokens'])}*")
            print(str(invokeMetrics))
            # Display rationale in an expander if enabled
            
            # if st.session_state.show_rationale and rationale != "No rationale available":
            #     with st.expander("Agent Rationale"):
            #         st.code(rationale, language="json")
            # Add assistant response to chat history
            print(str(writestream))
            print("==================================================END=================================================\n\n\n\n")
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": writestream,
                "metrics": invokeMetrics
            })
else:
    st.info("Please select both an agent and an alias from the sidebar to start chatting.")

