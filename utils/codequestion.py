from langchain_openai import ChatOpenAI,OpenAI
from dotenv import load_dotenv
from langchain.schema import SystemMessage,HumanMessage,AIMessage

import os 
from langchain.prompts.prompt import PromptTemplate
load_dotenv()
from langchain.chains import SequentialChain,LLMChain
def loadcode(topic):
    llm=ChatOpenAI()

    question_prompt=PromptTemplate.from_template(template="""
         generate a detailed coding question on  topic {topic} to
         be solved using java with only one static method with some return type,
         also provide example inputs and outputs
        """)
    chain_quest=LLMChain(llm=llm,prompt=question_prompt,output_key="question")
    
    class_outline=PromptTemplate.from_template(template="""
        for the question {question}, Give a class(dont use public class) and add
 a static method that represents the solution and do not fill the code for the
static method just have a comment  // your code here
        """)
    chain_outline=LLMChain(llm=llm,prompt=class_outline,output_key="outline")

    test_cases=PromptTemplate.from_template(template="""
    Given the code outline {outline}, Generate a class Named TestClass with
    method public Integer test() and come up with 10 test cases to test the method
    in the code outline and returns the number of test cases passed.
                                         """)
    chain_test=LLMChain(llm=llm,prompt=test_cases,output_key="testcases")
 
    chain_of_chains=SequentialChain(
      chains=[chain_quest,chain_outline,chain_test],
      input_variables=["topic"],
     output_variables=["question","outline","testcases"]
    )

    result=chain_of_chains.invoke({"topic": topic})

    print(result)
    return result