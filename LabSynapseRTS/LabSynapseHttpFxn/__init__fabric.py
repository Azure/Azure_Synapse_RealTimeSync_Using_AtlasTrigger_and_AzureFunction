import json
import logging
import os
import requests
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

# Code to create get token
def get_access_token():
    """It will create a access token to access the mail apis"""
    app_id = os.environ["app_id"]      #Application Id - on the azure app overview page
    client_secret = os.environ["client_secret"]
    directory_id = os.environ["directory_id"]
    token_url = "https://login.microsoftonline.com/"+directory_id+"/oauth2/v2.0/token"
    token_data = {
    "grant_type": "client_credentials",
    "client_id": app_id,
    "client_secret": client_secret,
    "scope":"https://storage.azure.com/.default"
    }
    token_headers={
      "Content-Type":"application/x-www-form-urlencoded"
    }
    print(token_url)
    token_response = requests.post(token_url,data=token_data,headers=token_headers)
    token_response_dict = json.loads(token_response.text)

    print(token_response.text)

    token = token_response_dict.get("access_token")

    if token == None :
      print("Unable to get access token")
      print(str(token_response_dict))
      raise Exception("Error in getting in access token")
    else:
      print("Token is:" + token)
      return token
         
def patch_file(access_token,encoded_data): 
    print("Access token is :" + access_token)
    storage_file_name = os.environ["storage_file_name"]
    token_url = "https://onelake.dfs.fabric.microsoft.com/OneLake/Lakehouse02.Lakehouse/Files/Imported/" + storage_file_name + "?resource=file"
    token_headers={
        "Authorization" : "Bearer " + access_token,
        "content-length" : "0"
    }
    print("creating file in lake")

    # Code to create file in lakehouse
    response = requests.put(token_url, data={}, headers=token_headers)
    print(response)
    
    token_url = "https://onelake.dfs.fabric.microsoft.com/OneLake/Lakehouse02.Lakehouse/Files/Imported/" + storage_file_name + "?position=0&action=append&flush=true"
    token_headers={
        "Authorization" : "Bearer " + access_token,
        "x-ms-file-name": storage_file_name 
    }
    print(token_url)
    print("pushing data to file in lake")

    response = requests.patch(token_url, data=encoded_data, headers=token_headers)
        
    print(response)

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a new request.')
    logging.info(req)
    #object_id = req.get_body().__getitem__(0)
    json_data = req.get_body()
    logging.info(json_data)
    object_id = "test"
    try:
        json_string = json_data.decode("utf-8")
        json_object = json.loads(json_string)
        if json_object["operationType"] == "delete":
           object_id = json_object["fullDocumentBeforeChange"]["_id"]["$oid"]
           data = {"operationType": json_object["operationType"], "data":json_object["fullDocumentBeforeChange"]}
        else:
           object_id = json_object["fullDocument"]["_id"]["$oid"]
           data = {"operationType": json_object["operationType"], "data":json_object["fullDocument"]}
       
        logging.info(object_id)
        encoded_data = json.dumps(data)
    except Exception as e:
        logging.info("Exception occured : "+ str(e)) 

    access_token = get_access_token()   
    patch_file(access_token,encoded_data)
    return func.HttpResponse(f"This HTTP triggered function executed successfully.")   
