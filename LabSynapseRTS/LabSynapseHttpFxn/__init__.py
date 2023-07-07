import json
import logging
import os
import azure.functions as func
from azure.storage.filedatalake import DataLakeServiceClient

def main(req: func.HttpRequest) -> func.HttpResponse:
   logging.info('Python HTTP trigger function processed a new request.')
   logging.info(req)
   storage_account_name = os.environ["storage_account_name"]
   storage_account_key = os.environ["storage_account_key"]
   storage_container = os.environ["storage_container"]
   storage_directory = os.environ["storage_directory"]
   storage_file_name = os.environ["storage_file_name"]
   service_client = DataLakeServiceClient(account_url="{}://{}.dfs.core.windows.net".format(
           "https", storage_account_name), credential=storage_account_key)
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
       
   file_system_client = service_client.get_file_system_client(file_system=storage_container)
   directory_client = file_system_client.get_directory_client(storage_directory)
   file_client = directory_client.create_file(storage_file_name + "-" + str(object_id) + ".txt")
   file_client.append_data(data=encoded_data, offset=0, length=len(encoded_data))
   file_client.flush_data(len(encoded_data))
   return func.HttpResponse(f"This HTTP triggered function executed successfully.")
