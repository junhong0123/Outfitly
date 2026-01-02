using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Outfitly.Data;
using Outfitly.Models;
using System.Security.Claims;

namespace Outfitly.Controllers
{
    public class CartController : Controller
    {
        private readonly ApplicationDbContext _context;
        private readonly UserManager<IdentityUser> _userManager;

        public CartController(ApplicationDbContext context, UserManager<IdentityUser> userManager)
        {
            _context = context;
            _userManager = userManager;
        }

        // GET: Cart
        public async Task<IActionResult> Index()
        {
            // If not logged in, show empty cart with message
            if (!User.Identity?.IsAuthenticated ?? true)
            {
                ViewBag.Message = "Please log in to view your cart.";
                return View(new Cart());
            }

            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);

            // Get cart items from database
            var cartItems = await _context.CartItems
                .Include(c => c.Product)
                .Where(c => c.UserId == userId)
                .Select(c => new CartItemViewModel
                {
                    Id = c.Id,
                    ProductId = c.ProductId,
                    ProductName = c.Product != null ? c.Product.Name : "Unknown Product",
                    Price = c.Product != null ? c.Product.Price : 0,
                    Quantity = c.Quantity,
                    ImageUrl = c.Product != null ? c.Product.ImageUrl : null
                })
                .ToListAsync();

            var cart = new Cart { Items = cartItems };
            return View(cart);
        }

        // POST: Cart/Add
        [HttpPost]
        public async Task<IActionResult> Add(int productId, int quantity = 1, string? size = null, string? color = null)
        {
            // CRUCIAL CHECK: If user is NOT logged in, redirect to login
            if (!User.Identity?.IsAuthenticated ?? true)
            {
                // Set ReturnUrl to product page so user can return after login
                var returnUrl = Url.Action("Details", "Products", new { id = productId });
                return Redirect($"/Identity/Account/Login?ReturnUrl={Uri.EscapeDataString(returnUrl ?? "/")}");
            }

            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrEmpty(userId))
            {
                return Redirect("/Identity/Account/Login");
            }

            // Check if product exists
            var product = await _context.Products.FindAsync(productId);
            if (product == null)
            {
                TempData["Error"] = "Product not found.";
                return RedirectToAction("Index", "Products");
            }

            // Check if item already exists in cart
            var existingItem = await _context.CartItems
                .FirstOrDefaultAsync(c => c.UserId == userId && c.ProductId == productId);

            if (existingItem != null)
            {
                // Increment quantity
                existingItem.Quantity += quantity;
                _context.CartItems.Update(existingItem);
            }
            else
            {
                // Create new cart item
                var cartItem = new CartItem
                {
                    UserId = userId,
                    ProductId = productId,
                    Quantity = quantity,
                    DateCreated = DateTime.UtcNow
                };
                await _context.CartItems.AddAsync(cartItem);
            }

            // Log UserInteraction for AI training (Type: "AddToCart")
            var interaction = new UserInteraction
            {
                UserId = userId,
                ProductId = productId,
                InteractionType = "AddToCart",
                TimeStamp = DateTime.UtcNow
            };
            await _context.UserInteractions.AddAsync(interaction);

            await _context.SaveChangesAsync();

            TempData["Success"] = $"{product.Name} added to cart!";
            return RedirectToAction("Details", "Products", new { id = productId });
        }

        // POST: Cart/Update
        [HttpPost]
        public async Task<IActionResult> Update(int cartItemId, int quantity)
        {
            if (!User.Identity?.IsAuthenticated ?? true)
            {
                return Json(new { success = false, message = "Please log in to update cart" });
            }

            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            var cartItem = await _context.CartItems
                .FirstOrDefaultAsync(c => c.Id == cartItemId && c.UserId == userId);

            if (cartItem == null)
            {
                return Json(new { success = false, message = "Item not found" });
            }

            if (quantity <= 0)
            {
                _context.CartItems.Remove(cartItem);
            }
            else
            {
                cartItem.Quantity = quantity;
                _context.CartItems.Update(cartItem);
            }

            await _context.SaveChangesAsync();
            return Json(new { success = true, message = "Cart updated" });
        }

        // POST: Cart/Remove
        [HttpPost]
        public async Task<IActionResult> Remove(int cartItemId)
        {
            if (!User.Identity?.IsAuthenticated ?? true)
            {
                return Json(new { success = false, message = "Please log in to modify cart" });
            }

            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            var cartItem = await _context.CartItems
                .FirstOrDefaultAsync(c => c.Id == cartItemId && c.UserId == userId);

            if (cartItem == null)
            {
                return Json(new { success = false, message = "Item not found" });
            }

            _context.CartItems.Remove(cartItem);
            await _context.SaveChangesAsync();

            return Json(new { success = true, message = "Item removed from cart" });
        }

        // GET: Cart/Count
        public async Task<IActionResult> Count()
        {
            if (!User.Identity?.IsAuthenticated ?? true)
            {
                return Json(new { count = 0 });
            }

            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            var count = await _context.CartItems
                .Where(c => c.UserId == userId)
                .SumAsync(c => c.Quantity);

            return Json(new { count = count });
        }
    }
}
