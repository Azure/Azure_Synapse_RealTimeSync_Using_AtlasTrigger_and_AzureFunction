# Real Time Sync from MongoDB Atlas to Azure Synapse using Atlas Trigger and Azure Function
## Background:
Azure Synapse is used by multiple customers as a one stop solution for their analytical needs. Data is ingested from disparate sources into Synapse Dedicated SQL Pools (EDW) and SQL, AI/ ML, Batch, Spark based analytics can be performed and data is further visualized using tools like Power BI. 

MongoDB has both a [Source and Sink connector](https://learn.microsoft.com/en-us/azure/data-factory/connector-mongodb?tabs=data-factory) for Synapse pipelines which enables fetching data from MongoDB or loading data into MongoDB in batches/ micro batches.

However, currently there is no CDC connector for MongoDB in Synapse to keep the Synapse dedicated SQL pools synced with MongoDB data in real time. To facilitate real time analytics, MongoDB with Microsoft provided a custom solution and gave it as a few clicks and configuration based deployment as detailed [here](https://learn.microsoft.com/en-us/azure/architecture/example-scenario/analytics/azure-synapse-analytics-integrate-mongodb-atlas). There is however still a need to provide a more seamless integration for real time sync from MongoDB to Synapse. MongoDB Atlas Trigger and Azure function can be combined to help here.

## Solution Overview:
This simple solution uses [Atlas triggers](https://www.mongodb.com/docs/atlas/app-services/triggers/) and [functions](https://www.mongodb.com/docs/atlas/app-services/functions/) which abstracts the code needed to set up change streams and take an action based on the change detected.

![Picture 1](https://user-images.githubusercontent.com/104025201/230293199-a7acbd10-1a42-42e8-9491-f1dc0e5fd096.png)

### Workflow:
1. Set up a change stream on one of the collections using MongoDB Triggers.
2. MongoDB function writes the changes captured to Azure functions.
3. Azure function writes the data to synapse ADLS gen2.

In this lab we will use “sample_mflix.movies” namespace from the sample dataset as source for the change stream data. Thus, any changes made into this collection will add a blog in the Synapse ADLS gen2 storage.

### Prerequisites:
You will need the below set up before starting the Lab:
- **MongoDB Atlas cluster setup:** 
  
  Register for a new Atlas account [here](https://www.mongodb.com/docs/atlas/tutorial/create-atlas-account/#register-a-new-service-account). 
  
  Follow steps from 1 to 4 (*Create an Atlas account*, *Deploy a free cluster*, *Add your IP to the IP access list* and *Create Database user*) to set up  
  the Atlas environment.
  
  Also, follow step 7 “*Load Sample Data*” to load sample data to be used in the lab.
  
![Picture 2](https://user-images.githubusercontent.com/104025201/230300219-6f95d9be-616f-4267-8cce-e4d3af5d1411.png)


  **Note: For this lab, add “0.0.0.0/0” to the IP access list so that Synapse can connect to MongoDB Atlas. In production scenarios, It is recommended to use Private link or VNET peering instead of the IP whitelisting.**
  
- **Azure account setup:**
  
  Follow link [here](https://azure.microsoft.com/en-in/free/) to set up a free azure account
 
- **Azure Synapse Analytics workspace setup:**
  Follow link [here](https://learn.microsoft.com/en-us/azure/synapse-analytics/get-started-create-workspace) to set up a Synapse workspace within you Azure account

### Integration Steps:

1. **Fetch ADLS Gen2 storage details** 

   Go to Azure account, search for Storage Accounts and select your default ADLS Gen2 storage associated with your Synapse workspace (“*labmdbsynapseadls*” in the example). You can always check the ADLS Gen2 account name and the default container name in your Synapse workspace, under “*Data*” tile on left and under the “*Linked*” tab.
   
    - Note down the default container under “*Containers*” under the “*Data storage*” section. (“*defaultprimary*” in the example)
    - You can create a directory under this Container or just give a name of your choice and the code will create it. (“*newcreate*” in the example)
    - Give any name for the storage_file_name (“*labsynapse*” in the example)
    - Go to the “*Access keys*” tab under “*Security + networking*” and copy one of the access keys.

<img width="452" alt="Picture 3" src="https://user-images.githubusercontent.com/104025201/230335335-76916e1d-77b1-49a1-b9b7-0f1c930074f6.png">

Save all this information in a notepad as :

    storage_account_name = labmdbsynapseadls                                                              
    storage_account_key =  <your access key>                                                              
    storage_container = defaultprimary                                                                      
    storage_directory = newcreate                                                                             
    storage_file_name = labsynapse
  
  2. **Set Up Azure Function**
  
  **i.** Create an HTTP triggered function app using [Visual Studio Code](https://learn.microsoft.com/en-us/azure/azure-functions/create-first-function-vs-code-python?pivots=python-mode-configuration) or [command line](https://learn.microsoft.com/en-us/azure/azure-functions/create-first-function-cli-python?tabs=azure-cli%2Cbash&pivots=python-mode-configuration).

  Replace the sample code with the below code in “__init__.py”:

  ```
    import json
    import logging
    import os
    import azure.functions as func
    from azure.identity import DefaultAzureCredential
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
      #object_id = req.get_body().__getitem__(0)
      json_data = req.get_body()
      logging.info(json_data)
      object_id = "test"
      try:
          json_string = json_data.decode("utf-8")
          json_object = json.loads(json_string)
          object_id = json_object["_id"]["$oid"]
          logging.info(object_id)
      except Exception as e:
          logging.info("Exception occurred : "+ str(e))   
      file_system_client = service_client.get_file_system_client(file_system=storage_container)
      directory_client = file_system_client.get_directory_client(storage_directory)
      file_client = directory_client.create_file(storage_file_name + "-" + str(object_id) + ".txt")
      file_client.append_data(data=json_data, offset=0, length=len(json_data))
      file_client.flush_data(len(json_data))
      return func.HttpResponse(f"This HTTP triggered function executed successfully.")
  ```   
  
      
  **ii.** Add the below to the *requirements.txt* file which already has *azure-functions*
      
  ```
  azure-identity                                                                                                    
  Azure-storage-file-datalake
  ```
  
  **iii.** Deploy the local project from Workspace Local to Azure. Select the upload to cloud icon and select the *Deploy to Function App* option. It will prompt you to select the Function App name on the top bar. Once  selected, you can see the deployment progress in the OUTPUT window of the terminal.

<img width="452" alt="Picture 4" src="https://user-images.githubusercontent.com/104025201/230351875-180d03cf-5c82-46e1-b228-820520c9777c.png">


  **iv.** Add the storage related parameters to the Application Settings section under the Function App on Azure. Right click on “Application Settings” and select “Add New Setting”. Enter the new setting name and value when prompted. Add all the 5 storage account related values saved in Step [Fetch ADLS Gen2 Storage Details](https://docs.google.com/document/d/1n1ppHjSjbU-Rn-QtUvIVXHwmScdS6xfcejoVnID4JnQ/edit#heading=h.74dcpfke4uzb)  to the Application Settings.

  ![Picture 5](https://user-images.githubusercontent.com/104025201/230347931-ebd1d66a-10ee-42a2-9e6a-1aed4cb26592.png)
  
  **v.** Deploy the application again by repeating step 4. This time look out for the deployment success message on the bottom right and select the “Upload settings”. This will update the newly added settings. 

![Picture 6](https://user-images.githubusercontent.com/104025201/230348257-3ff54005-493f-4ecf-9aa6-006a271fcaad.png)

   You can verify the settings by going to the Azure function and checking the “Configuration”  
   tab under the “Settings” section.
   
 ![Picture 7](https://user-images.githubusercontent.com/104025201/230348513-c941a71f-d26b-4343-9780-442d0c091f3d.png)
 
  **vi.** Note the Azure function url from the deployment logs 

![Picture 8](https://user-images.githubusercontent.com/104025201/230348744-627d5ca0-1102-4615-ab96-876afb16a205.png)

  You can also get the function url by navigating to the function in Azure and selecting “Get 
  Function Url”.
  
![Picture 9](https://user-images.githubusercontent.com/104025201/230349002-abfff2e9-54c8-45aa-84ec-0ddd36ffad1b.png)

2. **Set Up Atlas Trigger**
  
  **i.** Select “Triggers” tile under “SERVICES” on the left of the Atlas UI. This will open the Trigger Homepage. Select the “Add Trigger” button on the top right to create a new trigger for our movies collection.
  
  ![Picture 10](https://user-images.githubusercontent.com/104025201/230365556-f393c737-d2fe-40e3-95ff-e588b5c949e2.png)

  **ii.** Let the default “Database Trigger” remain so, give a name for the trigger (LabSynapse in the example). Link the “Sandbox” cluster. Don't change any other settings.
  
  ![Picture 11](https://user-images.githubusercontent.com/104025201/230365615-fe3e2082-8354-4f3d-ac88-584c26a16093.png)

  **iii.** Under “TRIGGER SOURCE DETAILS”, Select the “Cluster Name” as “Sandbox” “Database Name” as “sample_mflix” and select the “Collection Name” as “movies”. Select the Operation Type as “Insert” and also Select the “Full Document” option.
  
![Picture 12](https://user-images.githubusercontent.com/104025201/230365652-7f40426d-5a1f-4cc4-84c9-3ff5d4ab21af.png)

  **iv.** Let the “Select An Event Type” option under “FUNCTION” remain selected as “Function”. Remove all the sample code and paste the below code in the box.

```
    exports =  function(changeEvent) {  
    const fullDocument = changeEvent.fullDocument;

    // Invoke Azure function inserting the change stream into ADLS gen2

    console.log(typeof fullDocument);
    const response =  context.http.post({
      url: "https://<azure_functon_url>.azurewebsites.net/api/<azure_functon_url>http",
      body: fullDocument,
      encodeBodyAsJSON: true
    });
    return response;
};
```

**Note**: The url needs to be replaced with your Azure function url from Step 6 of Set Up Azure Function

![Picture 13](https://user-images.githubusercontent.com/104025201/230365858-ffb65c0d-d177-4da4-91cc-0944a1b8db39.png)

  **v.** Click “Save” at the bottom to Save the newly created Trigger. Once Saved, going back to Triggers Home page we can see our newly added Trigger.

Now that the Trigger is enabled, it will watch the movies collection for any “Insert” operations and trigger our Azure function in the event of the insertion of a document.
  
  ![Picture 14](https://user-images.githubusercontent.com/104025201/230365975-2f6a2c69-ef69-45b9-a889-2069238eccb9.png)



