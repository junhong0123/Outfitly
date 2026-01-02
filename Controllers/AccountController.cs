using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Authorization;
using Microsoft.EntityFrameworkCore;
using Outfitly.Data;
using Outfitly.Models;
using System.Security.Claims;

namespace Outfitly.Controllers
{
    [Authorize]
    public class AccountController : Controller
    {
        private readonly ApplicationDbContext _context;
        private readonly UserManager<IdentityUser> _userManager;

        public AccountController(ApplicationDbContext context, UserManager<IdentityUser> userManager)
        {
            _context = context;
            _userManager = userManager;
        }

        // GET: Account/MyOrders
        public async Task<IActionResult> MyOrders(string? status = null)
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrEmpty(userId))
            {
                return Redirect("/Identity/Account/Login?ReturnUrl=/Account/MyOrders");
            }

            // Fetch orders with OrderItems and Products
            var ordersQuery = _context.Orders
                .Include(o => o.OrderItems)
                .ThenInclude(oi => oi.Product)
                .Where(o => o.UserId == userId)
                .OrderByDescending(o => o.OrderDate);

            // Filter by status if provided
            if (!string.IsNullOrEmpty(status) && status.ToLower() != "all")
            {
                ordersQuery = (IOrderedQueryable<Order>)ordersQuery.Where(o => o.Status.ToLower() == status.ToLower());
            }

            var orders = await ordersQuery.ToListAsync();

            ViewBag.SelectedStatus = status ?? "all";
            return View(orders);
        }

        // GET: Account/OrderDetails/{id}
        public async Task<IActionResult> OrderDetails(int id)
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);

            var order = await _context.Orders
                .Include(o => o.OrderItems)
                .ThenInclude(oi => oi.Product)
                .FirstOrDefaultAsync(o => o.Id == id && o.UserId == userId);

            if (order == null)
            {
                return NotFound();
            }

            return View(order);
        }

        // GET: Account/Dashboard
        public async Task<IActionResult> Dashboard()
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            var user = await _userManager.GetUserAsync(User);

            if (user == null)
            {
                return Redirect("/Identity/Account/Login");
            }

            var orders = await _context.Orders
                .Include(o => o.OrderItems)
                .Where(o => o.UserId == userId)
                .OrderByDescending(o => o.OrderDate)
                .ToListAsync();

            var dashboardData = new DashboardViewModel
            {
                UserName = user.UserName ?? "User",
                UserEmail = user.Email ?? "",
                TotalOrders = orders.Count,
                PendingOrders = orders.Count(o => o.Status == "Pending" || o.Status == "Processing"),
                TotalSpent = orders.Sum(o => o.TotalAmount),
                RecentOrders = orders.Take(3).ToList()
            };

            return View(dashboardData);
        }

        // POST: Account/CancelOrder
        [HttpPost]
        public async Task<IActionResult> CancelOrder(int orderId)
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            var order = await _context.Orders
                .FirstOrDefaultAsync(o => o.Id == orderId && o.UserId == userId);

            if (order == null)
            {
                return Json(new { success = false, message = "Order not found" });
            }

            // Only allow cancellation if order is Pending
            if (order.Status != "Pending")
            {
                return Json(new { success = false, message = "Only pending orders can be cancelled" });
            }

            order.Status = "Cancelled";
            await _context.SaveChangesAsync();

            return Json(new
            {
                success = true,
                message = "Order cancelled successfully."
            });
        }
    }
}
