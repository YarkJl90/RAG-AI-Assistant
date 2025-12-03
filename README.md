# Maquina KANIKI - Chatbot with RAG and Flask

This project is a chatbot web application built with Flask that integrates a Retrieval-Augmented Generation (RAG) system to answer questions based on a set of PDF documents.

## Features

-   **Flask Backend**: Lightweight and robust web server.
-   **Modern Chat Interface**: Clean UI inspired by major AI platforms.
-   **RAG System**: Ability to "talk" to your documents thanks to `langchain` and `ChromaDB`.
-   **Conversation Memory**: The chatbot remembers previous interactions in a session.
-   **Flexible Configuration**: Control model parameters (like temperature) and RAG settings from the interface.
-   **Professional Project Structure**: Organized to be scalable and easy to maintain, with defined dependencies and environment.

## Project Structure

The project is organized following best practices for Flask applications, ensuring no import errors and an intuitive structure.

```
chatbot-flask/
│
├── chatbot_flask/             # The main Flask application package
│   ├── __init__.py          # Turns the directory into a Python package
│   ├── app.py               # Main Flask logic, routes, and endpoints
│   ├── rag.py               # Module for performing semantic searches (RAG)
│   ├── rag_build.py         # Script to (re)build the vector database
│   ├── chat_memory.db       # SQLite database for conversation memory
│   │
│   ├── static/              # Static files (CSS, JS, images)
│   │   ├── style.css
│   │   ├── script.js
│   │   └── images/
│   │       └── logo.png
│   │       └── bg.jpg
│   │
│   └── templates/           # Flask HTML templates
│       └── index.html
│
├── documents/                 # Directory for your PDF and TXT files
│
├── vectorstore/               # Vector database storage (ChromaDB)
│
├── venv/                      # Python virtual environment
│
├── .env                       # Configuration file for environment variables (API Keys)
├── .gitignore                 # Files and folders ignored by Git
├── README.md                  # This file
├── requirements.txt           # List of Python dependencies
└── run.sh                     # Script to start the application
```

## Installation

Follow these steps to set up and run the project in your local environment.

### 1. Clone the Repository

```bash
git clone <REPOSITORY_URL>
cd chatbot-flask
```

### 2. Create and Activate the Virtual Environment

It is essential to use a virtual environment to isolate project dependencies.

```bash
# Create the virtual environment (only needs to be done once)
python3 -m venv venv

# Activate the environment (you must do this every time you work on the project)
source venv/bin/activate
```

### 3. Install Dependencies

Install all necessary Python libraries with `pip`.

```bash
pip install -r requirements.txt
```

### 4. Configure the OpenAI API Key

The project needs an OpenAI API key to work.

1.  Open the `.env` file and replace `YOUR_KEY_HERE` with your secret OpenAI API key.

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PYTHONPATH=.
```

## RAG System (Retrieval-Augmented Generation)

### How does it work?

The RAG system allows the chatbot to access information external to its base model. In this project:

1.  **Ingestion**: The `rag_build.py` script reads the PDF files from the `/documents` folder.
2.  **Chunking**: It divides the documents into small text fragments.
3.  **Embedding**: Each fragment is converted into a numerical vector using an embeddings model (`all-MiniLM-L6-v2`).
4.  **Indexing**: The vectors are stored in a vector database (`ChromaDB`) in the `/vectorstore` folder.
5.  **Search**: When you send a message with RAG enabled, your question is also converted into a vector.
6.  **Retrieval**: ChromaDB searches for the text fragments most semantically similar to your question.
7.  **Augmentation**: The retrieved fragments are injected into the prompt sent to OpenAI, giving the model the necessary context to answer based on your documents.

### How to add new documents?

Simply **add your `.pdf` or `.txt` files to the `/documents` folder**.

### How to regenerate the vector database?

After adding or deleting documents, you must regenerate the RAG index by following these steps:

1.  **Activate the virtual environment**:
    Make sure you are in the project's virtual environment.
    ```bash
    source venv/bin/activate
    ```

2.  **Run the build script**:
    This script will delete the old vector database and create a new one with the documents currently in the `/documents` folder.
    ```bash
    python3 -m chatbot_flask.rag_build
    ```

3.  **Refresh the application's memory**:
    For efficiency, the web application keeps the vector database loaded in memory. You must tell it to reload the new database by sending a request to a special endpoint.

    You can do this with the following `curl` command in your terminal, or by restarting the Flask server (`./run.sh`).
    ```bash
    curl -X POST http://127.0.0.1:5000/refresh-rag
    ```

This process ensures that your chatbot uses the most up-to-date information.

## How to Run the Application

We have prepared a `run.sh` script that simplifies the execution process.

### 1. Grant Execution Permissions to the Script

This step only needs to be done once.

```bash
chmod +x run.sh
```

### 2. Start the Server

```bash
./run.sh
```

The script will handle activating the virtual environment, setting up environment variables, and launching the Flask application.

Once running, you can access the chatbot in your browser at `http://127.0.0.1:5000`.

---
*Audit and reorganization by Gemini.*
