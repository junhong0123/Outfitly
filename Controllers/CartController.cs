using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
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
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);

            if (string.IsNullOrEmpty(userId))
            {
                // For unauthenticated users, we can redirect to login or show an empty cart
                // prompting them to login.
                // Requirement: "If not logged in... redirect" (specifically for Add).
                // For Index, asking for login seems appropriate for a persistent cart logic.
                return Redirect($"/Identity/Account/Login?returnUrl={Uri.EscapeDataString("/Cart")}");
            }

            var cartItems = await _context.CartItems
                .Where(c => c.UserId == userId)
                .ToListAsync();

            return View(cartItems);
        }

        // POST: Cart/Add
        [HttpPost]
        public async Task<IActionResult> Add(int productId, int quantity = 1, string? size = null, string? color = null)
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrEmpty(userId))
            {
                // If the user is not logged in, redirect them to the Login page 
                // Since this is likely an AJAX call, returning a JSON with redirect info or 401 is better,
                // but the requirement "return a response that triggers the login flow" often means 
                // returning a challenge or specific JSON.
                // Assuming the frontend handles 401 or we return a JSON indicating requirement.
                return Json(new { success = false, redirectUrl = "/Identity/Account/Login" });
            }

            var product = await _context.Products.FindAsync(productId);
            if (product == null)
            {
                return Json(new { success = false, message = "Product not found" });
            }

            // Check if item already exists for this user
            var existingItem = await _context.CartItems
                .FirstOrDefaultAsync(c => c.UserId == userId &&
                                          c.ProductId == productId &&
                                          c.Size == size &&
                                          c.Color == color);

            if (existingItem != null)
            {
                existingItem.Quantity += quantity;
                _context.Update(existingItem);
            }
            else
            {
                var newItem = new CartItem
                {
                    UserId = userId,
                    ProductId = productId,
                    ProductName = product.Name,
                    Price = product.Price,
                    Quantity = quantity,
                    Size = size,
                    Color = color,
                    ImageUrl = product.ImageUrl
                };
                _context.CartItems.Add(newItem);
            }

            await _context.SaveChangesAsync();

            return Json(new { success = true, message = "Product added to cart" });
        }

        // POST: Cart/Update
        [HttpPost]
        public async Task<IActionResult> Update(int cartItemId, int quantity)
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrEmpty(userId)) return Unauthorized();

            var cartItem = await _context.CartItems
                .FirstOrDefaultAsync(c => c.Id == cartItemId && c.UserId == userId);

            if (cartItem != null)
            {
                if (quantity > 0)
                {
                    cartItem.Quantity = quantity;
                    _context.Update(cartItem);
                }
                else
                {
                    _context.CartItems.Remove(cartItem);
                }
                await _context.SaveChangesAsync();
                return Json(new { success = true, message = "Cart updated" });
            }

            return Json(new { success = false, message = "Item not found" });
        }

        // POST: Cart/Remove
        [HttpPost]
        public async Task<IActionResult> Remove(int cartItemId)
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrEmpty(userId)) return Unauthorized();

            var cartItem = await _context.CartItems
                .FirstOrDefaultAsync(c => c.Id == cartItemId && c.UserId == userId);

            if (cartItem != null)
            {
                _context.CartItems.Remove(cartItem);
                await _context.SaveChangesAsync();
                return Json(new { success = true, message = "Item removed from cart" });
            }

            return Json(new { success = false, message = "Item not found" });
        }

        // GET: Cart/Count
        public async Task<IActionResult> Count()
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            int count = 0;

            if (!string.IsNullOrEmpty(userId))
            {
                count = await _context.CartItems
                    .Where(c => c.UserId == userId)
                    .SumAsync(c => c.Quantity);
            }

            return Json(new { count = count });
        }
    }
}