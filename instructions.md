# Agent Instructions: Outfitly Project Development

## 1. Role & Objective
You are an expert Full-Stack .NET Developer. Your goal is to continue the development of "Outfitly," an online clothing store.
The project uses a **Hybrid Architecture**:
* **Customer-Facing Store:** ASP.NET Core MVC (Standard Web App).
* **Admin Dashboard:** Blazor Server (Integrated into the same app).
* **Styling:** Tailwind CSS (v4.1).
* **Database:** Microsoft SQL Server.
* **AI Integration:** The system must be prepared to connect with a Python Microservice later (for Chatbot & Recommendations).

## 2. Project Context
* **Auth:** ASP.NET Core Identity (already set up).
* **Styling:** Tailwind is configured. Output file is at `wwwroot/css/output.css`.
* **Current State:** Basic MVC controllers exist. Blazor needs to be configured.

## 3. Database Schema (Strict Compliance Required)
Use Entity Framework Core. You must ensure these exact tables exist to support the future AI module.

* **`Products` Table:** `Id`, `Name`, `Price`, `Description`, `ImageUrl`, `Category` (string), `Stock` (int).
* **`Orders` Table:** `Id`, `UserId`, `TotalAmount`, `OrderDate`, `Status`, `ShippingAddress`.
* **`OrderItems` Table:** `Id`, `OrderId`, `ProductId`, `Quantity`, `PriceAtPurchase`.
* **`CartItems` Table:** `Id`, `UserId`, `ProductId`, `Quantity`, `DateCreated`.
* **`UserInteractions` Table (CRITICAL FOR AI):** * `Id` (PK)
    * `UserId` (FK to AspNetUsers)
    * `ProductId` (FK to Products)
    * `InteractionType` (string: "View", "AddToCart", "Purchase")
    * `TimeStamp` (DateTime)

## 4. Implementation Tasks

### Part A: Customer Portal (ASP.NET Core MVC)
* **Styling Rule:** Use **Tailwind CSS utility classes** only (e.g., `grid`, `flex`, `p-4`, `rounded-lg`). Do not use Bootstrap.

1.  **Product Catalog & Data Logging:**
    * Update `ProductsController`.
    * **Logic (AI Prep):** In the `Details` action, if a user is logged in, **create a record in `UserInteractions`** with type "View". This is required for training the recommendation model later.
    * **UI:** Create a responsive grid (`grid-cols-2 md:grid-cols-4`) for the Index page.

2.  **Product Details Page (`Details.cshtml`):**
    * Display full product info.
    * **UI Placeholder (AI):** Add a distinct section below the product details titled **"Recommended for You"**. Leave it empty or put a "Loading recommendations..." placeholder text for now. (This will be populated via AJAX/Python API later).

3.  **Shopping Cart & Checkout:**
    * Ensure `CartController` saves to `CartItems` database table (persistent cart).
    * Implement `CheckoutController` to convert `CartItems` -> `Order` + `OrderItems`.
    * **Logic (AI Prep):** When an order is placed, log a "Purchase" interaction in `UserInteractions` for each item.

4.  **Layout & Chatbot (`_Layout.cshtml`):**
    * **UI Placeholder (AI):** Add a **floating action button** (icon) at the bottom-right of the screen.
    * Styling: `fixed bottom-4 right-4 bg-indigo-600 text-white p-4 rounded-full shadow-lg z-50`.
    * Label/Tooltip: "Chat with AI Stylist".

### Part B: Admin Dashboard (Blazor Server)
* **Configuration:**
    * Update `Program.cs` to add `builder.Services.AddServerSideBlazor()` and `app.MapBlazorHub()`.
    * Create a `_Host.cshtml` or update Layout to support Blazor components.
* **Styling:** Use Tailwind CSS for the admin layout (Sidebar + Content Area).

1.  **Admin Layout:**
    * Create `Shared/AdminLayout.razor`.
    * Include a Sidebar with links to "Products" and "Orders".

2.  **Product Management (`/admin/products`):**
    * Create a Blazor Component: `Pages/Admin/Products.razor`.
    * **Features:**
        * Data Grid: Display products with Edit/Delete buttons.
        * **Add/Edit Modal:** A form to create/update products (Name, Price, Category, ImageUrl).
    * **Security:** Use `@attribute [Authorize(Roles = "Admin")]`.

3.  **Order Management (`/admin/orders`):**
    * Create `Pages/Admin/Orders.razor`.
    * List all orders showing User, Date, Total, and **Status**.
    * Allow Admin to update Status (e.g., dropdown to change "Pending" to "Shipped").

## 5. Coding Constraints
* **Dependency Injection:** Inject `ApplicationDbContext` into Controllers and Blazor Components (use `IDbContextFactory` for Blazor if strictly necessary, or scoped service).
* **Data Seed:** Create a `DbInitializer` class to seed 1 Admin User (email: `admin@outfitly.com`) and 10 sample Products if the DB is empty.
* **Verification:**
    1.  Clicking a product in MVC must add a row to `UserInteractions` table.
    2.  Accessing `/admin/products` without Admin login must redirect or show Access Denied.