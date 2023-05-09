#!/Users/mark/dev/ml/langchain/read_github/langchain_github/env/bin/python
# change above to the location of your local Python venv installation
import sys, os

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

import pathlib

from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain.text_splitter import PythonCodeTextSplitter
from langchain.chat_models import ChatOpenAI
from my_llm import standards as my_llm
from my_llm.langchain_class import PubSubChatMessageHistory
from langchain import PromptTemplate

chat = ChatOpenAI(temperature=0.4)

# Get Markdown documents from a repository
def get_repo_docs(repo_path, extension, memory):
    repo = pathlib.Path(repo_path)
    
    ignore = 'env/'
    if config['ignore']:
        ignore = config['ignore']  

    ignore_path = repo / ignore
    if not ignore_path.is_dir():
        print("WARNING: --ignore must be a directory")
    
    print('Ignoring %s' % ignore_path)
    
    exts = extension.split(",")
    for ext in exts:
        the_glob = f"**/*{ext}"
        matched_files = list(repo.glob(the_glob))
        num_matched_files = len(matched_files)
        print(f"Number of matched {ext} files: {num_matched_files}")

        # Generate summary md files
        if ext!=".md":
            k = 0
            for non_md_file in repo.glob(the_glob):
                k += 1
                if str(non_md_file).startswith(str(ignore_path)):
                      continue
                generate_code_summary(non_md_file, memory)
                if config['verbose']:
                    print(f"Generated summary for a {ext} file: {k} of {num_matched_files} done.")
                              
		# Iterate over all files in the repo (including subdirectories)
        print(f"Reading {ext} files")
        i = 0
        j = 0
        for md_file in repo.glob(the_glob):

            if str(md_file).startswith(str(ignore_path)):
                j += 1
                continue
            
            i += 1
			# Read the content of the file
            try:
                with open (md_file, "r") as file:
                    rel_path = md_file.relative_to(repo)
                    metadata = {"source": str(rel_path)}
                    #print(metadata)
                    yield Document(page_content=file.read(), metadata=metadata)
            except Exception as e:
                print(f"Error reading {md_file}: " + str(e))
            
            if config['verbose']:
                print(f"Read {i} files so far and ignored {j}: total: {num_matched_files}")
        
        print(f"Read {i} and ignored {j} {ext} files.")
        
    print("Read all files")

# Function to summarise code from the OpenAI API     
def generate_code_summary(a_file, memory):
    
    new_file_name = a_file.with_suffix('.md')
    if os.path.isfile(new_file_name) and not config['resummarise']:
         if config['verbose']:
            print(f"Skipping generating summary as found existing code summary file: {new_file_name}")
         return

    with open(a_file, "r") as file:
        code = file.read()
    
    if len(code) < 10:
        if config['verbose']:
            print(f"Skipping generation as not enough information.  Got: {code}")
        return

    print("================================================")
    print(f"Requesting code summary for {a_file}   ")
    print("================================================")

    source_chunks = []
    splitter = PythonCodeTextSplitter()
    for chunk in splitter.split_text(code):
        source_chunks.append(Document(page_content=chunk, metadata={"source": a_file}))    

    # create prompt to pass in to LLM
    template = """
Summarise what the code does below.  Use Markdown in your output with the following template:

# a title
summary of script purpose

## keywords
Comma seperated list of 3-4 keywords suitable for this code

## classes
A description of each class

## functions/methods
How the functions or methods of a class work including listing the Inputs and outputs for each function

## code examples of use

The code to summarise is here:
{code}
"""

    prompt = PromptTemplate(
        input_variables=["code"],
        template=template,
    )
    
    new_file_name = a_file.with_suffix('.md')

    for chunk in source_chunks:
        summary = my_llm.request_llm(
            prompt.format(code=chunk.page_content), 
            chat, 
            memory,
            metadata={'task':'summarise_code'})
    
        my_llm.save_to_file(new_file_name, summary + '\n\n', type = "a")
    
    return
    
# Get source chunks from a repository
def get_source_docs(repo_path, extension, memory):
    source_chunks = []

    splitter = CharacterTextSplitter(separator=" ", chunk_size=1024, chunk_overlap=0)
    for source in get_repo_docs(repo_path, extension, memory):
        if extension == ".py":
            splitter = PythonCodeTextSplitter()
        for chunk in splitter.split_text(source.page_content):
            source_chunks.append(Document(page_content=chunk, metadata=source.metadata))

    return source_chunks

def setup_memory(config):

    memory = PubSubChatMessageHistory("qna_documents")

    if config['reindex']:
		# Create a new Chroma DB
        exts = '.md,.py'
        if config['ext']:
            exts = config['ext']
        source_chunks = get_source_docs(config['repo'], exts, memory=memory)
        memory.save_vectorstore_memory(source_chunks)

    return memory 



def main(config):

    memory = setup_memory(config)
	
    while True:
        print('\n\033[31m' + '=Ask a question. CTRL + C to quit.')
        print ("=If I don't know, tell me so I can learn and answer more accurately next time"  + '\033[m')
        user_input = input()
        print('\033[31m')
        answer = memory.question_memory(user_input, llm=chat, verbose=config['verbose'])
        if answer is not None:
            if answer.get('source_documents') is not None:
                print('\n== Document sources:')
                i = 0
                for doc in answer.get('source_documents'):
                    i += 1
                    print(f'-- Source {i}')
                    print(f' - page_content:\n {doc.page_content}')
                    if config['verbose']:
                        print(f' - metadata: \n{doc.metadata}')

            print('\n================================')
            print('== Answer:\n\n' + answer['result'])

        else:
             print('Sorry')

        print('\033[m')

def document_to_dict(document):
    return {
        'page_content': document.page_content,
        'metadata': document.metadata,
    }

def process_input(user_input: str, 
                  repo: str=None, 
                  reindex: bool =False, 
                  ext: str='.py,.md', 
                  ignore: str='env/', 
                  resummarise: bool =False, 
                  verbose: bool =True):

    # this is only needed if you need to recreate the vectorstore
    config = {
        'repo': repo,
        'reindex': reindex,
        'ext': ext,
        'ignore': ignore,
        'resummarise': resummarise,
        'verbose': verbose
    }
    
    memory = setup_memory(config)
    answer = memory.question_memory(user_input, llm=chat, verbose=verbose)

    response = {'result': answer['result']}
    if answer.get('source_documents') is not None:
        source_documents = [document_to_dict(doc) for doc in answer['source_documents']]
        response['source_documents'] = source_documents

    return response


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description="Chat with a GitHub repository",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("repo", help="The GitHub repository on local disk")
    parser.add_argument("--reindex", action="store_true", 
                        help="Whether to re-index the doc database that supply context to the Q&A")
    parser.add_argument("--ext", help="Comma separated list of file extensions to include. Defaults to '.md,.py'")
    parser.add_argument("--ignore", help="Directory to ignore file imports from. Defaults to 'env/'")
    parser.add_argument("--resummarise", action="store_true", help="Recreate the code.md files describing the code")
    parser.add_argument("--verbose", action="store_true", help="Include metadata such as sources in replies")
    args = parser.parse_args()
    config = vars(args)

    try:
        main(config)
    except KeyboardInterrupt:
        print('  - User exit.')
        sys.exit(1)