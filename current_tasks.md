# Implementation Tasks: Backend Integration & User Flow

We have completed the basic UI for Part A. Now we need to connect the Backend Logic and finalize the User Flow.
Please execute the following tasks step-by-step.

## Context
* **Database:** Use existing `ApplicationDbContext`.
* **Auth:** Use `User.Identity.IsAuthenticated` and `UserManager`.
* **Styling:** Use Tailwind CSS only.

## Step 1: Smart "Add to Cart" Logic (CartController)
**File:** `Controllers/CartController.cs`
**Requirement:**
1.  Update the `AddToCart` POST action.
2.  **Crucial Check:** If the user is **NOT logged in**:
    * Do NOT add to database.
    * Redirect them specifically to the Login page (`/Identity/Account/Login`).
    * Set the `ReturnUrl` so after logging in, they come back to the product page.
3.  If logged in:
    * Check if `CartItem` exists. If yes, increment quantity. If no, create new.
    * Save to Database.
    * Add a record to `UserInteractions` table (Type: "AddToCart").
    * Show a success notification (TempData).

## Step 2: Full Checkout Flow (CheckoutController)
**File:** `Controllers/CheckoutController.cs` & `Views/Checkout/Index.cshtml`
**Requirement:**
1.  **Index (GET):** Calculate `TotalAmount` from `CartItems` and pass to View.
2.  **PlaceOrder (POST):**
    * Create a new `Order` record (Status: "Pending", Date: Now).
    * Loop through `CartItems` -> Create `OrderItems`.
    * **AI Data Logging:** For each item purchased, add a record to `UserInteractions` (Type: "Purchase").
    * **Cleanup:** Remove all `CartItems` for this user after successful order.
    * Redirect to a "Order Confirmation" page.

## Step 3: "My Orders" History
**File:** `Controllers/AccountController.cs` (or create `OrdersController.cs`)
**Requirement:**
1.  Create an action `MyOrders`.
2.  Fetch data: `_context.Orders.Include(o => o.OrderItems).ThenInclude(oi => oi.Product).Where(u => u.UserId == currentUserId)`.
3.  Create the View `Views/Account/MyOrders.cshtml`.
4.  **UI:** Display orders in a clean list/card format using Tailwind. Show "Date", "Total", "Status", and a list of items inside each order.

## Step 4: AI Chatbot Widget (Popup UI)
**File:** `Views/Shared/_Layout.cshtml`
**Requirement:**
1.  We do NOT want a separate page for Chat. It must be a **Floating Popup**.
2.  Add a "Chat Icon" button fixed at the **bottom-right** of the screen (`fixed bottom-5 right-5`).
3.  Add a hidden Chat Window container (`div`) anchored above the button.
4.  **JavaScript:** Add simple JS to toggle the `hidden` class of the Chat Window when the button is clicked.
5.  **Styling:** The window should look like a messenger app (Header, Message Area, Input Box).