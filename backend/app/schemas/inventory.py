from pydantic import BaseModel, Field

class InventoryBalance(BaseModel):
    balance_id: int; product_id: int; location_id: int; quantity: int; reserved_quantity: int; available_quantity: int

class Availability(BaseModel):
    product_id: int; quantity: int; reserved_quantity: int; available_quantity: int
