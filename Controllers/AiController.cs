using System.Security.Claims;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Outfitly.Data;
using Outfitly.Models;
using Outfitly.Services;

namespace Outfitly.Controllers
{
    [ApiController]
    [Route("[controller]")]
    public class AiController : ControllerBase
    {
        private readonly AiEngineClient _aiEngineClient;
        private readonly ApplicationDbContext _context;

        public AiController(AiEngineClient aiEngineClient, ApplicationDbContext context)
        {
            _aiEngineClient = aiEngineClient;
            _context = context;
        }

        [HttpPost("Chat")]
        public async Task<IActionResult> Chat([FromBody] AiChatRequest request, CancellationToken cancellationToken)
        {
            if (string.IsNullOrWhiteSpace(request.Message))
            {
                return BadRequest(new { answer = "Please enter a message.", sources = Array.Empty<AiSource>() });
            }

            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            var topK = Math.Clamp(request.TopK, 1, 8);
            var response = await _aiEngineClient.ChatAsync(request.Message.Trim(), userId, topK, cancellationToken);
            await EnrichProductSourcesAsync(response.Sources, cancellationToken);

            return Ok(response);
        }

        private async Task EnrichProductSourcesAsync(List<AiSource> sources, CancellationToken cancellationToken)
        {
            var productIds = sources
                .Where(source => source.Type.Equals("product", StringComparison.OrdinalIgnoreCase) && source.Id.HasValue)
                .Select(source => source.Id!.Value)
                .Distinct()
                .ToList();

            if (!productIds.Any())
            {
                return;
            }

            var products = await _context.Products
                .Where(product => productIds.Contains(product.Id))
                .ToListAsync(cancellationToken);

            var productById = products.ToDictionary(product => product.Id);
            foreach (var source in sources)
            {
                if (!source.Id.HasValue || !productById.TryGetValue(source.Id.Value, out var product))
                {
                    continue;
                }

                source.Title = product.Name;
                source.Price = product.Price;
                source.ImageUrl = product.ImageUrls.FirstOrDefault();
                source.Url = Url.Action("Details", "Products", new { id = product.Id }) ?? $"/Products/Details/{product.Id}";
            }
        }
    }
}
