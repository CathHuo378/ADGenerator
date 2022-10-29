# ADGenerator
System developed for Topics in Computer Science

Date: 2022-10-29

Version: 1.1.1


## PURPOSE
`ADGenerator` is a graph-based tool for the simulation of realistic Active Directory environments. The graph models are generated according to a customizable list of requirements and represent the relationships between the nodes of an Active Directory domain. Finally, graphs are stored in a Neo4j graph database instance. This tool is inspired by [adsimulator](https://github.com/nicolas-carolo/adsimulator) but implements a tiered structure to enhance the security of an Active Directory domain.


## MINIMUM REQUIREMENTS

## Supported OS
* Linux
* macOS

## Interpreter and tools
* Python 3
* Neo4j


## INSTALLATION

### Linux
1. Install **Neo4j**
2. Create a new Neo4j database instance with the following credentials:
   * Username: `neo4j`
   * Password: `password`
3. Install `apoc` plugin
4. Append the following lines to the settings file:
   ```
   apoc.import.file.enabled=true
   apoc.import.file.use_neo4j_config=false
   apoc.export.file.enabled=true
   ```

### macOS
1. Install **Neo4j**
2. Create a new Neo4j database instance with the following credentials:
   * Username: `neo4j`
   * Password: `password`
3. Install `apoc` plugin
4. Append the following lines to the settings file:
   ```
   apoc.import.file.enabled=true
   apoc.import.file.use_neo4j_config=false
   apoc.export.file.enabled=true
   apoc.export.file.enabled=true
   ```

## USAGE

### Running
```
$ python adgenerator.py -seclev low/medium/high
```

### Commands

* `dbconfig` - Set the credentials and the database URL
* `connect` - Connect to the database using supplied credentials
* `setparams` - Import the settings JSON file containing the parameters for the graph generation. Here, a [template](./docs/settings.json) you can use for customizing setting and generate different Active Directory models.
* `setdomain` - Set the domain name
* `cleardb` - Clear the database and set the schema properly
* `generate` - Connect to the database, clear the DB, set the schema, and generate the random graph model. If you use this command followed by a file path (e.g., `generate /tmp/testlab.json`), you can export the graph model as a JSON file.
* `about`: View information about the version of the software
* `update`: Check for updates 
* `exit` - Exit

### View generated graph models

The generated graph models are available at `http://localhost:7474/`, where we can execute Cypher queries for generating graphs. Here, [some examples of Cypher queries](./docs/cypher_queries.md).

![Neo4j Web Interface](./img/neo4j.png)
