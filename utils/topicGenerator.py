from langchain_openai import ChatOpenAI,OpenAI
from dotenv import load_dotenv
from langchain.schema import SystemMessage,HumanMessage,AIMessage

import os 
from langchain.prompts.prompt import PromptTemplate
load_dotenv()
from langchain.chains import SequentialChain,LLMChain
def genConcept(subject):
    # Initialize the OpenAI model
    llm = ChatOpenAI()

    # Define the prompt template
    prompt_template = PromptTemplate.from_template(template="""
        Generate a list of topics for the subject: {subject} as a list of strings (no numbering, no bulleting)
    """)

    # Create the LLMChain with the prompt template
    chain = LLMChain(llm=llm, prompt=prompt_template, output_key="topics")

    # Run the chain to generate the topics
    result = chain.invoke({"subject": subject})

    # Extract topics from the response
    topics = result["topics"].split('\n')

    return {"subject": subject, "topics": topics}
