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


import random
import string


def generate_acta_id():

    letters = "".join(
        random.choice(string.ascii_uppercase)
        for _ in range(2)
    )

    numbers = "".join(
        random.choice(string.digits)
        for _ in range(3)
    )

    return f"PA-{letters}{numbers}"


def update_text_column(
    item_id,
    board_id,
    column_id,
    value
):

    q = """
    mutation (
        $board: ID!,
        $item: ID!,
        $column: String!,
        $value: String!
    ) {
      change_simple_column_value(
        board_id: $board,
        item_id: $item,
        column_id: $column,
        value: $value
      ) {
        id
      }
    }
    """

    graphql(
        q,
        {
            "board": str(board_id),
            "item": str(item_id),
            "column": column_id,
            "value": value,
        }
    )


def get_file_public_url(item, column_id):
    """Return the public URL of the first file uploaded to a file-type column, or None."""

    raw_value = None

    for c in item.get("column_values", []):
        if c["id"] == column_id:
            raw_value = c.get("value")
            break

    if not raw_value:
        return None

    try:
        parsed = json.loads(raw_value)
    except (TypeError, ValueError):
        return None

    files = parsed.get("files") or []

    if not files:
        return None

    asset_id = files[0].get("assetId") or files[0].get("asset_id")

    if not asset_id:
        return None

    q = """query ($ids: [ID!]!) {
        assets(ids: $ids) {
            public_url
        }
    }"""

    assets = graphql(q, {"ids": [str(asset_id)]})["assets"]

    return assets[0]["public_url"] if assets else None


def download_file(url, dest_path):
    """Download a file from a public URL to a local path."""

    response = requests.get(url, timeout=120)
    response.raise_for_status()

    Path(dest_path).write_bytes(response.content)

    return dest_path


def get_connected_person(item, connect_column_id, email_column_id):
    """Resolve a Connect Boards column to (name, email) of the linked item.

    The name comes from the linked item's own name; the email from a
    column on that linked item (e.g. a "Gerentes" board with one item per
    person). Returns (None, None) if nothing is linked. Restricting who
    can be picked is a property of the connected board itself (only items
    that exist there are selectable) and of who can edit that board - not
    something this function needs to enforce.
    """

    raw_value = None

    for c in item.get("column_values", []):
        if c["id"] == connect_column_id:
            raw_value = c.get("value")
            break

    if not raw_value:
        return None, None

    try:
        parsed = json.loads(raw_value)
    except (TypeError, ValueError):
        return None, None

    linked_ids = [
        str(p["linkedPulseId"])
        for p in (parsed.get("linkedPulseIds") or [])
        if p.get("linkedPulseId")
    ]

    if not linked_ids:
        return None, None

    q = """query ($ids: [ID!]!) {
        items(ids: $ids) {
            name
            column_values {
                id
                text
            }
        }
    }"""

    items = graphql(q, {"ids": linked_ids})["items"]

    if not items:
        return None, None

    linked_item = items[0]
    name = linked_item.get("name")
    email = None

    for c in linked_item.get("column_values", []):
        if c["id"] == email_column_id:
            email = (c.get("text") or "").strip() or None
            break

    return name, email


def create_update(item_id, body):
    """Post an update (comment) on an item - shows in its activity feed."""

    q = """mutation ($item: ID!, $body: String!) {
        create_update(item_id: $item, body: $body) {
            id
        }
    }"""

    graphql(q, {"item": str(item_id), "body": body})
