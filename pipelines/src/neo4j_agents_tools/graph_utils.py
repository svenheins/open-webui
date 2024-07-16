from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable


class Neo4jConnector:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        try:
            self.driver.verify_connectivity()
        except ServiceUnavailable:
            print(
                "neo4j service is not available: either the credentials are wrong or the database needs to be started."
            )

    def close(self):
        self.driver.close()

    def empty_graph(self):
        query = """
            MATCH (n) DETACH DELETE n
            """
        with self.driver.session() as session:
            result = session.run(query)
            return result

    def run_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return result

    def remove_relationships(self, id: str, type: str):
        query = "MATCH (n {id: '" + id + "'})-[r:" + type + "]->() DELETE r"
        self.run_query(query)

    def get_entity_by_id(self, id: str):

        records, summary, keys = self.driver.execute_query(
            "MATCH (p {id: $id}) RETURN properties(p) as prop",
            id=id,
            database_="neo4j",
        )

        # Loop through results and do something with them
        record = {}
        for entity in records:
            data_entity = entity.data()["prop"]
            record[data_entity["id"]] = {}
            for property in data_entity:
                record[data_entity["id"]][property] = data_entity[property]

        # Summary information
        print(
            "The query `{query}` returned {records_count} records in {time} ms.".format(
                query=summary.query,
                records_count=len(records),
                time=summary.result_available_after,
            )
        )

        if record:
            return record
        return None

    def get_entity_by_attributes(self, attributes: dict):
        where_clause_list = []
        for key in attributes:
            if isinstance(attributes[key], str):
                key_value = "'" + str(attributes[key]) + "'"
            else:
                key_value = str(attributes[key])
            where_clause_list.append("e." + key + " = " + key_value)
        where_clause = " AND ".join(where_clause_list)
        query = f"""MATCH (e)
        WHERE {where_clause}
        RETURN properties(e) as prop, labels(e) as labels
        """
        records, summary, keys = self.driver.execute_query(
            query,
            database_="neo4j",
        )

        record = {}
        for entity in records:
            data_entity = entity.data()["prop"]
            labels = entity.data()["labels"]
            record[data_entity["id"]] = {"type": ",".join(labels)}
            for property in data_entity:
                record[data_entity["id"]][property] = data_entity[property]

        if record:
            return record
        return None

    def get_relationship_by_attributes(self, attributes: dict):
        where_clause_list = []
        for key in attributes:
            if isinstance(attributes[key], str):
                key_value = "'" + str(attributes[key]) + "'"
            else:
                key_value = str(attributes[key])
            where_clause_list.append("r." + key + " = " + key_value)
        where_clause = " AND ".join(where_clause_list)
        query = f"""MATCH (e)-[r]->(f)
        WHERE {where_clause}
        RETURN properties(r) as prop, e.id as start_id, f.id as end_id, type(r) as type
        """
        records, summary, keys = self.driver.execute_query(
            query,
            database_="neo4j",
        )

        record = {}
        for entity in records:
            start_id = entity.data()["start_id"]
            end_id = entity.data()["end_id"]
            relationship_type = entity.data()["type"]
            data_entity = entity.data()["prop"]
            record[data_entity["id"]] = {
                "type": relationship_type,
                "start_id": start_id,
                "end_id": end_id,
            }
            for property in data_entity:
                record[data_entity["id"]][property] = data_entity[property]

        if record:
            return record
        return None

    def sync_link_to_neo4j(
        self,
        link_type: str = "KNOWS",
        dict_link: dict = None,
        symmetrical: bool = False,
        dict_attributes: dict = None,
    ):
        symmetrical_statement = ""
        symmetrical_attributes = ""
        if symmetrical:
            symmetrical_statement = "MERGE (b)-[r2:" + link_type + "]->(a)"
            symmetrical_attributes = ", r2 = $dict_link"
            if dict_attributes != None:
                symmetrical_attributes = (
                    symmetrical_attributes
                    + ", "
                    + ", ".join(
                        [f"r2.{k} = $attributes.{k}" for k in dict_attributes.keys()]
                    )
                )
        attributes_statement = ""
        if dict_attributes != None:
            attributes_statement = f"""
                ON CREATE SET r = $dict_link, {", ".join([f"r.{k} = $attributes.{k}" for k in dict_attributes.keys()])}{symmetrical_attributes}
                ON MATCH SET r = $dict_link, {", ".join([f"r.{k} = $attributes.{k}" for k in dict_attributes.keys()])}{symmetrical_attributes}
                """
        else:
            attributes_statement = f"""
                ON CREATE SET r = $dict_link {symmetrical_attributes}
                ON MATCH SET r = $dict_link {symmetrical_attributes}
                """

        query = (
            f"""
        MATCH (a {{id: $start_id}})
        MATCH (b {{id: $end_id}})
        MERGE (a)-[r:{link_type}]->(b)
        {symmetrical_statement}
        """
            + attributes_statement
        )
        parameters = {
            "start_id": dict_link["start_id"],
            "end_id": dict_link["end_id"],
            "dict_link": dict_link,
            "attributes": dict_attributes,
        }
        self.run_query(query, parameters)

    def sync_entity_to_neo4j(
        self,
        entity_type: str = "Character",
        dict_entity: dict = None,
        dict_attributes: dict = None,
    ):
        attributes_statement = ""
        if dict_attributes != None:
            attributes_statement = f"""
                ON CREATE SET {", ".join([f"p.{k} = $attributes.{k}" for k in dict_attributes.keys()])}
                ON MATCH SET {", ".join([f"p.{k} = $attributes.{k}" for k in dict_attributes.keys()])}
                """
        query = (
            f"""
        MERGE (p:{entity_type} {{id: $id}})
        ON CREATE SET p = $dict_entity
        ON MATCH SET p = $dict_entity
        """
            + attributes_statement
        )
        parameters = {
            "dict_entity": dict_entity,
            "id": dict_entity["id"],
            "attributes": dict_attributes,
        }
        self.run_query(query, parameters)
