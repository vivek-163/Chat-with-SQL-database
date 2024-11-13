import streamlit as st
from pathlib import Path
from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine
import sqlite3
from langchain_groq import ChatGroq

st.set_page_config(page_title="SQLMate", page_icon="🦜")
st.title("🦜 SQLMate : Chat with SQL DB")

LOCALDB="USE_LOCALDB"
MYSQL="USE_MYSQL"

radio_opt=["Use SQLLite 3 Database- Student.db","Connect to you MySQL Database"]

# selected_opt=st.sidebar.radio(label="Choose the DB which you want to chat",options=radio_opt)

# Make the label above the radio button larger with Markdown
st.sidebar.markdown("## Choose the Database You Want to Chat With")
selected_opt = st.sidebar.radio(label="", options=radio_opt)


mysql_host = mysql_user = mysql_password = mysql_db = None

if radio_opt.index(selected_opt)==1:
    db_uri=MYSQL
    mysql_host=st.sidebar.text_input("Provide MySQL Host")
    mysql_user=st.sidebar.text_input("MYSQL User")
    mysql_password=st.sidebar.text_input("MYSQL password",type="password")
    mysql_db=st.sidebar.text_input("MySQL database")
else:
    db_uri=LOCALDB

api_key=st.sidebar.text_input(label="GRoq API Key",type="password")

if not db_uri:
    st.info("Please enter the database information and uri")

if not api_key:
    st.info("Please add the groq api key")

## LLM model
llm=ChatGroq(groq_api_key=api_key,model_name="Llama3-8b-8192",streaming=True)

@st.cache_resource(ttl="2h")
def configure_db(db_uri,mysql_host=None,mysql_user=None,mysql_password=None,mysql_db=None):
    if db_uri==LOCALDB:
        dbfilepath=(Path(__file__).parent/"student.db").absolute()
        print(dbfilepath)
        creator = lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro", uri=True)
        return SQLDatabase(create_engine("sqlite:///", creator=creator))
    elif db_uri==MYSQL:
        if not (mysql_host and mysql_user and mysql_password and mysql_db):
            st.error("Please provide all MySQL connection details.")
            st.stop()
        return SQLDatabase(create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"))   
    
if db_uri==MYSQL:
    db=configure_db(db_uri,mysql_host,mysql_user,mysql_password,mysql_db)
else:
    db=configure_db(db_uri)

## toolkit
toolkit=SQLDatabaseToolkit(db=db,llm=llm)

agent=create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)

if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

user_query=st.chat_input(placeholder="Ask anything from the database")

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        streamlit_callback=StreamlitCallbackHandler(st.container())
        response=agent.run(user_query,callbacks=[streamlit_callback])
        st.session_state.messages.append({"role":"assistant","content":response})
        st.write(response)





# Existing imports here...

def display_schema(db):
    try:
        # Fetch tables using SQLAlchemy's `get_table_names` method
        tables = db.get_table_names()
        st.sidebar.write("### Database Schema")
        
        # Determine the type of database
        dialect_name = db._engine.dialect.name
        
        for table in tables:
            st.sidebar.write(f"**{table}**")
            
            # SQLite specific command to get column details
            if dialect_name == 'sqlite':
                query = f"PRAGMA table_info({table});"
                column_details = db._engine.execute(query).fetchall()
                for column in column_details:
                    col_name, col_type = column[1], column[2]
                    st.sidebar.write(f"- {col_name} ({col_type})")
                    
            # MySQL specific command to get column details
            elif dialect_name == 'mysql':
                query = f"""
                SELECT COLUMN_NAME, DATA_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = '{table}';
                """
                column_details = db._engine.execute(query).fetchall()
                for col_name, col_type in column_details:
                    st.sidebar.write(f"- {col_name} ({col_type})")
            
            # Add more conditions if you plan to support other databases
            else:
                st.sidebar.write("Database type not supported for schema display.")
    
    except Exception as e:
        st.sidebar.error(f"Failed to retrieve schema: {str(e)}")


@st.cache_resource(ttl="2h")
def configure_db(db_uri, mysql_host=None, mysql_user=None, mysql_password=None, mysql_db=None):
    try:
        if db_uri == LOCALDB:
            dbfilepath = (Path(__file__).parent / "student.db").absolute()
            if not dbfilepath.exists():
                st.error("Local database file not found.")
                st.stop()
            creator = lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro", uri=True)
            return SQLDatabase(create_engine("sqlite:///", creator=creator))
        
        elif db_uri == MYSQL:
            if not (mysql_host and mysql_user and mysql_password and mysql_db):
                st.error("Please provide all MySQL connection details.")
                st.stop()
            engine = create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}")
            return SQLDatabase(engine)
    
    except Exception as e:
        st.error(f"Failed to configure database: {str(e)}")
        st.stop()

if db_uri:
    db = configure_db(db_uri, mysql_host, mysql_user, mysql_password, mysql_db)
    display_schema(db)  # Show database schema in the sidebar
    if db:
        st.success("Connected to the database successfully!")

# Handle query history
if "query_history" not in st.session_state:
    st.session_state["query_history"] = []

if user_query:
    st.session_state["query_history"].append(user_query)
    st.sidebar.write("### Query History")
    for i, query in enumerate(st.session_state["query_history"], 1):
        st.sidebar.write(f"{i}. {query}")

# Remaining logic for handling user input, setting up the LLM, etc.
