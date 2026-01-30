from neo4j import GraphDatabase
import sys

uri = "neo4j+s://d037b471.databases.neo4j.io"
username = "neo4j"
password = "tc5LZhw0t7cRNoTa8PCEYhBH6ew4TShiDyBlWlpHcJk"

print(f"Testing connection to {uri}...")

def test_uri(test_uri):
    print(f"\n--- Testing {test_uri} ---")
    try:
        driver = GraphDatabase.driver(test_uri, auth=(username, password))
        with driver.session() as session:
            result = session.run("RETURN 1 as num")
            val = result.single()["num"]
            print(f"✓ Success! Result: {val}")
        driver.close()
    except Exception as e:
        print(f"✗ Failed: {e}")

test_uri("neo4j+s://d037b471.databases.neo4j.io")
test_uri("neo4j+ssc://d037b471.databases.neo4j.io")
test_uri("bolt+s://d037b471.databases.neo4j.io")
test_uri("bolt+ssc://d037b471.databases.neo4j.io")
