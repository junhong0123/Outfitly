using Microsoft.AspNetCore.Mvc;
using Outfitly.Models;

namespace Outfitly.Controllers
{
    public class CartController : Controller
    {
        // GET: Cart
        public IActionResult Index()
        {
            // TODO: Replace with actual cart data from session/database
            var cartItems = GetSampleCartItems();

            return View(cartItems);
        }

        // POST: Cart/Add
        [HttpPost]
        public IActionResult Add(int productId, int quantity = 1, string? size = null, string? color = null)
        {
            // TODO: Implement actual cart add logic
            // This would typically:
            // 1. Get product details from database
            // 2. Add to session/database cart
            // 3. Return success response

            return Json(new { success = true, message = "Product added to cart" });
        }

        // POST: Cart/Update
        [HttpPost]
        public IActionResult Update(int cartItemId, int quantity)
        {
            // TODO: Implement cart update logic
            // Update quantity in session/database

            return Json(new { success = true, message = "Cart updated" });
        }

        // POST: Cart/Remove
        [HttpPost]
        public IActionResult Remove(int cartItemId)
        {
            // TODO: Implement cart remove logic
            // Remove item from session/database

            return Json(new { success = true, message = "Item removed from cart" });
        }

        // GET: Cart/Count
        public IActionResult Count()
        {
            // TODO: Return actual cart item count
            int count = GetSampleCartItems().Count;

            return Json(new { count = count });
        }

        // Sample cart data for testing
        private List<CartItem> GetSampleCartItems()
        {
            return new List<CartItem>
            {
                new CartItem
                {
                    Id = 1,
                    ProductId = 1,
                    ProductName = "Minimal Cotton Tee",
                    Price = 49.00m,
                    Quantity = 1,
                    Color = "Black",
                    Size = "M",
                    ImageUrl = null
                },
                new CartItem
                {
                    Id = 2,
                    ProductId = 2,
                    ProductName = "Tailored Linen Pants",
                    Price = 89.00m,
                    Quantity = 2,
                    Color = "Blue",
                    Size = "L",
                    ImageUrl = null
                },
                new CartItem
                {
                    Id = 3,
                    ProductId = 3,
                    ProductName = "Leather Crossbody Bag",
                    Price = 129.00m,
                    Quantity = 1,
                    Color = "Brown",
                    Size = "One Size",
                    ImageUrl = null
                }
            };
        }
    }
}