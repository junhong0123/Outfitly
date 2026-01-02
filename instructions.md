# Agent Instructions: Outfitly Project Development

## 1. Role & Objective
You are an expert Full-Stack .NET Developer. Your goal is to continue the development of "Outfitly," an online clothing store.
The project uses a **Hybrid Architecture**:
* **Customer-Facing Store:** ASP.NET Core MVC.
* **Admin Dashboard:** Blazor Server (integrated into the same ASP.NET Core app).
* **Styling Framework:** Tailwind CSS.

## 2. Project Context
* **Database:** Microsoft SQL Server (via Entity Framework Core).
* **Auth:** ASP.NET Core Identity.
* **Current State:** Basic MVC controllers exist. Tailwind is configured (likely outputting to `wwwroot/css/output.css`).

## 3. Database Schema (Strict Compliance Required)
Use the existing Entity Framework models. Do not invent new tables.

* **`Products` Table:** `Id`, `Name`, `Price`, `Description`, `ImageUrl`, `Category`, `Stock`.
* **`Orders` Table:** `Id`, `UserId`, `TotalAmount`, `OrderDate`, `Status`, `ShippingAddress`.
* **`OrderItems` Table:** `Id`, `OrderId`, `ProductId`, `Quantity`, `PriceAtPurchase`.
* **`CartItems` Table:** `Id`, `UserId`, `ProductId`, `Quantity`, `DateCreated`.

## 4. Implementation Tasks

### Part A: Customer Portal (MVC)
* **Styling Rule:** All new Views must use **Tailwind CSS utility classes**. Do not use Bootstrap classes like `row` or `col-md-4`. Use `grid`, `flex`, `w-full`, etc.
1.  **Product Catalog:**
    * Update `ProductsController` and `Index.cshtml`.
    * **UI:** Create a responsive product grid using Tailwind (e.g., `grid-cols-1 md:grid-cols-3 gap-6`). Display product cards with images, prices, and an "Add to Cart" button styled with Tailwind (e.g., `bg-blue-600 hover:bg-blue-700 text-white rounded`).
2.  **Shopping Cart:**
    * Update `CartController` to persist items to `CartItems`.
    * **UI:** Design a clean cart summary table or list using Tailwind borders and spacing.
3.  **Checkout Process:**
    * Create `CheckoutController`.
    * On "Place Order": Create `Order`, move `CartItems` to `OrderItems`, clear cart.

### Part B: Admin Dashboard (Blazor Server)
* **Configuration:**
    * Update `Program.cs` to add `builder.Services.AddServerSideBlazor()` and `app.MapBlazorHub()`.
* **Admin Components:**
    * Create a Blazor layout or component wrapper that uses Tailwind CSS for the admin interface (Sidebar navigation, Data tables).
    * **Route `/admin/products`:** A Product Management Grid. Use Tailwind for the table layout (e.g., `table-auto w-full text-left`).
    * **Route `/admin/orders`:** Order Management View. Allow status updates.
* **Security:**
    * Protect these pages with `[Authorize(Roles = "Admin")]`.

## 5. Coding Constraints
* **Tailwind Integration:** Ensure class names are valid Tailwind utilities. If a build process is required (e.g., npm run build), mention it, but write the code assuming standard Tailwind classes work.
* **Dependency Injection:** Inject `ApplicationDbContext` where needed.
* **Verification:**
    1.  Verify the User flow (Cart -> Checkout) works.
    2.  Verify the Admin Blazor dashboard loads and looks correct with Tailwind styling.