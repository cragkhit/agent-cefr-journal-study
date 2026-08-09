from datetime import UTC, datetime

import discord
import pytz
from discord.ext import commands
from reactionmenu import Page, ViewButton, ViewMenu, ViewSelect

from bot import Tux
from ui.embeds import EmbedCreator, EmbedType
from utils.functions import generate_usage

timezones = {
    "North America": [
        ("🇺🇸", "US", "Pacific/Honolulu", "HST", -10),
        ("🇺🇸", "US", "America/Anchorage", "AKST", -9),
        ("🇺🇸", "US", "America/Los_Angeles", "PST", -8),
        ("🇺🇸", "US", "America/Denver", "MST", -7),
        ("🇺🇸", "US", "America/Chicago", "CST", -6),
        ("🇺🇸", "US", "America/New_York", "EST", -5),
        ("🇲🇽", "MX", "America/Mexico_City", "CST", -6),
        ("🇨🇦", "CA", "America/Toronto", "EST", -5),
        ("🇨🇦", "CA", "America/Vancouver", "PST", -8),
    ],
    "South America": [
        ("🇧🇷", "BR", "America/Sao_Paulo", "BRT", -3),
        ("🇦🇷", "AR", "America/Argentina/Buenos_Aires", "ART", -3),
        ("🇨🇱", "CL", "America/Santiago", "CLT", -3),
        ("🇵🇪", "PE", "America/Lima", "PET", -5),
        ("🇨🇴", "CO", "America/Bogota", "COT", -5),
        ("🇻🇪", "VE", "America/Caracas", "VET", -4),
        ("🇧🇴", "BO", "America/La_Paz", "BOT", -4),
        ("🇵🇾", "PY", "America/Asuncion", "PYT", -4),
        ("🇺🇾", "UY", "America/Montevideo", "UYT", -3),
    ],
    "Africa": [
        ("🇬🇭", "GH", "Africa/Accra", "GMT", 0),
        ("🇳🇬", "NG", "Africa/Lagos", "WAT", 1),
        ("🇿🇦", "ZA", "Africa/Johannesburg", "SAST", 2),
        ("🇪🇬", "EG", "Africa/Cairo", "EET", 2),
        ("🇰🇪", "KE", "Africa/Nairobi", "EAT", 3),
        ("🇲🇦", "MA", "Africa/Casablanca", "WET", 0),
        ("🇹🇿", "TZ", "Africa/Dar_es_Salaam", "EAT", 3),
        ("🇩🇿", "DZ", "Africa/Algiers", "CET", 1),
        ("🇳🇦", "NA", "Africa/Windhoek", "CAT", 2),
    ],
    "Europe": [
        ("🇬🇧", "GB", "Europe/London", "GMT", 0),
        ("🇩🇪", "DE", "Europe/Berlin", "CET", 1),
        ("🇫🇷", "FR", "Europe/Paris", "CET", 1),
        ("🇮🇹", "IT", "Europe/Rome", "CET", 1),
        ("🇪🇸", "ES", "Europe/Madrid", "CET", 1),
        ("🇳🇱", "NL", "Europe/Amsterdam", "CET", 1),
        ("🇧🇪", "BE", "Europe/Brussels", "CET", 1),
        ("🇷🇺", "RU", "Europe/Moscow", "MSK", 3),
        ("🇬🇷", "GR", "Europe/Athens", "EET", 2),
    ],
    "Asia": [
        ("🇦🇪", "AE", "Asia/Dubai", "GST", 4),
        ("🇮🇳", "IN", "Asia/Kolkata", "IST", 5.5),
        ("🇧🇩", "BD", "Asia/Dhaka", "BST", 6),
        ("🇲🇲", "MM", "Asia/Yangon", "MMT", 6.5),
        ("🇹🇭", "TH", "Asia/Bangkok", "ICT", 7),
        ("🇻🇳", "VN", "Asia/Ho_Chi_Minh", "ICT", 7),
        ("🇨🇳", "CN", "Asia/Shanghai", "CST", 8),
        ("🇭🇰", "HK", "Asia/Hong_Kong", "HKT", 8),
        ("🇯🇵", "JP", "Asia/Tokyo", "JST", 9),
    ],
    "Australia/Oceania": [
        ("🇦🇺", "AU", "Australia/Perth", "AWST", 8),
        ("🇦🇺", "AU", "Australia/Sydney", "AEST", 10),
        ("🇫🇯", "FJ", "Pacific/Fiji", "FJT", 12),
        ("🇳🇿", "NZ", "Pacific/Auckland", "NZDT", 13),
        ("🇵🇬", "PG", "Pacific/Port_Moresby", "PGT", 10),
        ("🇼🇸", "WS", "Pacific/Apia", "WSST", 13),
        ("🇸🇧", "SB", "Pacific/Guadalcanal", "SBT", 11),
        ("🇻🇺", "VU", "Pacific/Efate", "VUT", 11),
        ("🇵🇫", "PF", "Pacific/Tahiti", "THAT", -10),
    ],
}

continent_emojis = {
    "North America": "🌎",
    "South America": "🌎",
    "Africa": "🌍",
    "Europe": "🌍",
    "Asia": "🌏",
    "Australia/Oceania": "🌏",
}


class Timezones(commands.Cog):
    def __init__(self, bot: Tux) -> None:
        self.bot = bot
        self.timezones.usage = generate_usage(self.timezones)

    @commands.hybrid_command(
        name="timezones",
        aliases=["tz"],
    )
    async def timezones(self, ctx: commands.Context[Tux]) -> None:
        utc_now = datetime.now(UTC)

        menu = ViewMenu(ctx, menu_type=ViewMenu.TypeEmbed)

        default_embeds: list[discord.Embed] = []
        options: dict[discord.SelectOption, list[Page]] = {}

        for continent, tz_list in timezones.items():
            embeds: list[discord.Embed] = []
            pages = [tz_list[i : i + 9] for i in range(0, len(tz_list), 9)]

            for page in pages:
                embed = EmbedCreator.create_embed(
                    embed_type=EmbedType.INFO,
                    title=f"Timezones in {continent}",
                    custom_color=discord.Color.blurple(),
                )

                for flag, _country, tz_name, abbr, utc_offset in page:
                    tz = pytz.timezone(tz_name)
                    local_time = utc_now.astimezone(tz)
                    time_24hr = local_time.strftime("%H:%M")
                    time_12hr = local_time.strftime("%I:%M %p")

                    embed.add_field(
                        name=f"{flag} {abbr} (UTC{utc_offset:+.2f})",
                        value=f"`{time_24hr} | {time_12hr}`",
                        inline=True,
                    )

                embeds.append(embed)

            default_embeds.extend(embeds)

            options[discord.SelectOption(label=continent, emoji=continent_emojis[continent])] = Page.from_embeds(embeds)

        for embed in default_embeds:
            menu.add_page(embed)

        select = ViewSelect(title="Select Continent", options=options)
        menu.add_select(select)
        menu.add_button(ViewButton.end_session())

        await menu.start()


async def setup(bot: Tux) -> None:
    await bot.add_cog(Timezones(bot))
