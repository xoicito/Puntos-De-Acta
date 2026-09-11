import json
from pathlib import Path
import requests
from config import MONDAY_API_URL, MONDAY_FILE_URL, MONDAY_API_VERSION, MONDAY_TOKEN


class MondayError(RuntimeError):
    """Exception raised for Monday.com API errors."""
    pass


def _headers():
    """Get headers required for Monday.com API requests."""
    if not MONDAY_TOKEN:
        raise MondayError("Falta la variable de entorno MONDAY_TOKEN")
    return {
        "Authorization": MONDAY_TOKEN,
        "API-Version": MONDAY_API_VERSION,
        "Content-Type": "application/json"
    }


def graphql(query, variables=None):
    """Execute a GraphQL query against the Monday.com API."""
    response = requests.post(
        MONDAY_API_URL,
        headers=_headers(),
        json={
            "query": query,
            "variables": variables or {}
        },
        timeout=60
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("errors"):
        raise MondayError(json.dumps(payload["errors"], ensure_ascii=False))

    return payload["data"]


def get_item(item_id):
    """Fetch item details from Monday.com board."""
    q = """query ($ids: [ID!]!) {
        items(ids: $ids) {
            id
            name
            board { id }
            column_values { id text value type }
            subitems {
                id
                name
                column_values { id text value type }
            }
        }
    }"""

    items = graphql(q, {"ids": [str(item_id)]})["items"]

    if not items:
        raise MondayError(f"No existe el item {item_id}")

    return items[0]


def change_status(item_id, board_id, column_id, label):
    """Update the status of an item in Monday.com."""
    if not column_id:
        return

    q = """mutation ($board: ID!, $item: ID!, $column: String!, $value: JSON!) {
        change_column_value(
            board_id: $board,
            item_id: $item,
            column_id: $column,
            value: $value
        ) {
            id
        }
    }"""

    graphql(
        q,
        {
            "board": str(board_id),
            "item": str(item_id),
            "column": column_id,
            "value": json.dumps({"label": label})
        }
    )


def upload_file(item_id, column_id, file_path):
    """Upload a file to a Monday.com column."""
    if not column_id:
        return None

    query = (
        f"mutation ($file: File!) {{ "
        f"add_file_to_column(item_id: {item_id}, column_id: \"{column_id}\", file: $file) {{ id }} "
        f"}}"
    )

    operations = json.dumps({
        "query": query,
        "variables": {"file": None}
    })

    mapping = json.dumps({"file": ["variables.file"]})

    headers = {
        "Authorization": MONDAY_TOKEN,
        "API-Version": MONDAY_API_VERSION
    }

    with open(file_path, "rb") as f:
        response = requests.post(
            MONDAY_FILE_URL,
            headers=headers,
            data={
                "query": query,
                "operations": operations,
                "map": mapping
            },
            files={"file": (Path(file_path).name, f)},
            timeout=120
        )

    response.raise_for_status()
    payload = response.json()


from config import COTIZACION_BOARD_ID

def get_cotizacion_rows(acta_id):
    q = """
    query ($board: ID!) {
      boards(ids: [$board]) {
        items_page(limit: 500) {
          items {
            name
            column_values {
              id
              text
            }
          }
        }
      }
    }
    """

    boards = graphql(
        q,
        {"board": str(COTIZACION_BOARD_ID)}
    )["boards"]

    if not boards:
        return []

    rows = []

    for item in boards[0]["items_page"]["items"]:

        if (item.get("name") or "").strip() != acta_id:
            continue

        values = {
            c["id"]: c.get("text", "")
            for c in item["column_values"]
        }

        rows.append({
            "descripcion": values.get("text_mm73s8w0", ""),
            "unidad": values.get("text_mm73d37w", ""),
            "cantidad": values.get("text_mm73kpsc", ""),
            "precio": values.get("text_mm73qvb9", ""),
            "observaciones": values.get("text_mm734j2g", ""),
        })

    print("COTIZACION_ROWS =", rows)

    return rows

    if payload.get("errors"):
        raise MondayError(json.dumps(payload["errors"], ensure_ascii=False))

    return payload.get("data", {}).get("add_file_to_column", {}).get("id")
