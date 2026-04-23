# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
# ]
# ///

import requests
import time
from itertools import combinations
from collections import Counter

URL = "http://127.0.0.1:12346"
DECK = "RED"
STAKE = "WHITE"
SEED = None
DESIRED_RUNS = 0

RANK_ORDER = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
    "8": 8, "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
}

HAND_RANKINGS = [
    "High Card", "Pair", "Two Pair", "Three of a Kind",
    "Straight", "Flush", "Full House", "Four of a Kind",
    "Straight Flush", "Flush House", "Flush Five", "Five of a Kind",
]

HAND_BASE = {
    "High Card":      (5, 1),
    "Pair":           (10, 2),
    "Two Pair":       (20, 2),
    "Three of a Kind":(30, 3),
    "Straight":       (30, 4),
    "Flush":          (35, 4),
    "Full House":     (40, 4),
    "Four of a Kind": (60, 7),
    "Straight Flush": (100, 8),
    "Flush House":    (80, 8),
    "Flush Five":     (100, 12),
    "Five of a Kind": (120, 12),
}

JOKER_MULT = {"j_joker", "j_greedy_joker", "j_lusty_joker", "j_wrathful_joker",
    "j_gluttenous_joker", "j_jolly", "j_zany", "j_mad", "j_crazy", "j_droll",
    "j_half", "j_mystic_summit", "j_fibonacci", "j_even_steven", "j_ride_the_bus",
    "j_green_joker", "j_fortune_teller", "j_abstract", "j_raised_fist",
    "j_supernova", "j_gros_michel", "j_loyalty_card", "j_misprint", "j_banner"}

JOKER_CHIPS = {"j_sly", "j_wily", "j_clever", "j_devious", "j_crafty",
    "j_runner", "j_square", "j_blue_joker", "j_stone", "j_scary_face",
    "j_ice_cream", "j_odd_todd", "j_scholar", "j_banner"}

JOKER_XMULT = {"j_cavendish", "j_card_sharp", "j_hologram", "j_baron",
    "j_constellation", "j_steel_joker", "j_vampire", "j_obelisk",
    "j_lucky_cat", "j_baseball", "j_graph", "j_tri",
    "j_throwback", "j_ceremonial", "j_burglar"}

JOKER_UTILITY = {"j_four_fingers", "j_shortcut", "j_mime", "j_riff_raff",
    "j_pareidolia", "j_credit_card", "j_chaos", "j_delayed_grat",
    "j_burglar", "j_sixth_sense", "j_dna", "j_splash",
    "j_vagabond", "j_business", "j_todo_list", "j_faceless",
    "j_superposition", "j_mail"}

TAROT_ENHANCE = {
    "c_magician": ("LUCKY", 2),
    "c_empress": ("MULT", 2),
    "c_heirophant": ("BONUS", 2),
    "c_lovers": ("WILD", 1),
    "c_chariot": ("STEEL", 1),
    "c_justice": ("GLASS", 1),
    "c_devil": ("GOLD", 1),
    "c_tower": ("STONE", 1),
}

TAROT_SUIT_CONVERT = {
    "c_star": ("D", 3),
    "c_moon": ("C", 3),
    "c_sun": ("H", 3),
    "c_world": ("S", 3),
}

PLANET_HAND = {
    "c_pluto": "High Card", "c_mercury": "Pair", "c_uranus": "Two Pair",
    "c_venus": "Three of a Kind", "c_saturn": "Straight", "c_jupiter": "Flush",
    "c_earth": "Full House", "c_mars": "Four of a Kind", "c_neptune": "Straight Flush",
    "c_planet_x": "Five of a Kind", "c_ceres": "Flush House", "c_eris": "Flush Five",
}


def get_modifier(card, field, default=None):
    m = card.get("modifier", {})
    if isinstance(m, list):
        for item in m:
            if isinstance(item, dict) and field in item:
                return item[field]
        return default
    if isinstance(m, dict):
        return m.get(field, default)
    return default


def get_cost(card, field, default=0):
    c = card.get("cost", {})
    if isinstance(c, list):
        for item in c:
            if isinstance(item, dict) and field in item:
                return item[field]
        return default
    if isinstance(c, dict):
        return c.get(field, default)
    return default


def get_value(card, field, default=None):
    v = card.get("value", {})
    if isinstance(v, list):
        for item in v:
            if isinstance(item, dict) and field in item:
                return item[field]
        return default
    if isinstance(v, dict):
        return v.get(field, default)
    return default


def rpc(method: str, params: dict = None, retries: int = 30) -> dict:
    if params is None:
        params = {}
    for attempt in range(retries):
        try:
            response = requests.post(URL, json={
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": 1,
            }, timeout=5)
            data = response.json()
            if "error" in data:
                raise Exception(f"RPC error: {data['error']}")
            return data["result"]
        except requests.exceptions.ConnectionError:
            if attempt == 0:
                print("Waiting for BalatroBot API on port 12346...")
            time.sleep(1)
    raise Exception(f"Could not connect to BalatroBot API after {retries}s")


def classify_hand(cards):
    if not cards:
        return "High Card", 0

    ranks = [RANK_ORDER.get(get_value(c, "rank", "2"), 2) for c in cards]
    suits = [get_value(c, "suit", "H") for c in cards]
    rank_counts = Counter(ranks)
    is_flush = len(set(suits)) == 1
    sorted_ranks = sorted(set(ranks))
    is_straight = False
    if len(sorted_ranks) == 5:
        if sorted_ranks[-1] - sorted_ranks[0] == 4:
            is_straight = True
        if set(sorted_ranks) == {2, 3, 4, 5, 14}:
            is_straight = True

    counts = sorted(rank_counts.values(), reverse=True)

    if len(cards) == 5:
        if is_straight and is_flush:
            if len(set(suits)) == 1 and is_straight:
                if counts == [5]:
                    return "Flush Five", 10
                if counts == [3, 2]:
                    return "Flush House", 9
                return "Straight Flush", 8
        if counts == [5]:
            return "Five of a Kind", 11
        if counts == [4, 1]:
            return "Four of a Kind", 7
        if counts == [3, 2]:
            if is_flush:
                return "Flush House", 9
            return "Full House", 6
        if is_flush:
            return "Flush", 5
        if is_straight:
            return "Straight", 4
        if counts == [3, 1, 1]:
            return "Three of a Kind", 3
        if counts == [2, 2, 1]:
            return "Two Pair", 2
        if counts == [2, 1, 1, 1]:
            return "Pair", 1
        return "High Card", 0
    elif len(cards) == 4:
        if counts == [4]:
            return "Five of a Kind", 11
        if counts == [3, 1]:
            return "Four of a Kind", 7
        if counts == [2, 2]:
            return "Two Pair", 2
        if counts == [2, 1, 1]:
            return "Pair", 1
        return "High Card", 0
    elif len(cards) == 3:
        if counts == [3]:
            return "Three of a Kind", 3
        if counts == [2, 1]:
            return "Pair", 1
        return "High Card", 0
    elif len(cards) == 2:
        if counts == [2]:
            return "Pair", 1
        return "High Card", 0
    return "High Card", 0


def estimate_hand_score(cards, state):
    hand_name, hand_level_idx = classify_hand(cards)
    hands_info = state.get("hands", {})
    hand_info = hands_info.get(hand_name, {})
    chips = hand_info.get("chips", HAND_BASE.get(hand_name, (5, 1))[0])
    mult = hand_info.get("mult", HAND_BASE.get(hand_name, (5, 1))[1])
    card_chips = sum(max(RANK_ORDER.get(get_value(c, "rank", "2"), 2), 2) for c in cards)
    return (chips + card_chips) * mult, hand_name


def find_best_hand(state):
    hand_cards = state["hand"]["cards"]
    if not hand_cards:
        return [], "High Card", 0
    best_score = -1
    best_cards = []
    best_name = "High Card"
    for size in range(5, 0, -1):
        for combo in combinations(range(len(hand_cards)), size):
            cards = [hand_cards[i] for i in combo]
            score, name = estimate_hand_score(cards, state)
            if score > best_score:
                best_score = score
                best_cards = list(combo)
                best_name = name
        if best_score > 0 and size >= 3:
            break
    return best_cards, best_name, best_score


def cards_needed_for_score(state):
    blinds = state.get("blinds", {})
    current = None
    for b in blinds.get("cards", []):
        if b.get("blind", {}).get("status") == "CURRENT":
            current = b["blind"]
            break
    if not current:
        for b in blinds.get("cards", []):
            if b.get("blind", {}).get("status") == "SELECT":
                current = b["blind"]
                break
    target = current.get("score", 300) if current else 300
    round_info = state.get("round", {})
    hands_left = round_info.get("hands_left", 4)
    return target, hands_left


def choose_discards(state, best_indices, best_name):
    hand_cards = state["hand"]["cards"]
    round_info = state.get("round", {})
    discards_left = round_info.get("discards_left", 3)
    if discards_left <= 0:
        return None

    target, hands_left = cards_needed_for_score(state)
    best_cards = [hand_cards[i] for i in best_indices]
    best_score, _ = estimate_hand_score(best_cards, state)

    if best_score * hands_left >= target:
        return None

    keep_indices = set(best_indices)
    keep_suit = None
    if best_name == "Flush":
        suits = Counter(get_value(hand_cards[i], "suit", "H") for i in best_indices)
        keep_suit = suits.most_common(1)[0][0] if suits else None

    discard_indices = []
    for i, card in enumerate(hand_cards):
        if i in keep_indices:
            continue
        if keep_suit and get_value(card, "suit", "H") == keep_suit:
            continue
        rank = RANK_ORDER.get(get_value(card, "rank", "2"), 2)
        discard_indices.append((rank, i))

    discard_indices.sort(key=lambda x: x[0])
    result = [idx for _, idx in discard_indices[:5]]

    if not result:
        for i in range(len(hand_cards)):
            if i not in keep_indices:
                result.append(i)
        result = result[:5]

    return result if result else None


def joker_priority(joker_key):
    if joker_key in JOKER_XMULT:
        return 3
    if joker_key in JOKER_MULT:
        return 2
    if joker_key in JOKER_UTILITY:
        return 1
    if joker_key in JOKER_CHIPS:
        return 1
    return 0


def has_joker_synergy(joker_key, state):
    jokers = state.get("jokers", {}).get("cards", [])
    joker_keys = [j.get("key", "") for j in jokers]
    has_mult = any(k in JOKER_MULT for k in joker_keys)
    if joker_key in JOKER_XMULT and has_mult:
        return True
    if joker_key == "j_mime" and any(k in JOKER_XMULT for k in joker_keys):
        return True
    if joker_key == "j_four_fingers":
        return True
    return False


def handle_blind_select(state):
    blinds = state.get("blinds", {})
    for b in blinds.get("cards", []):
        blind = b.get("blind", {})
        if blind.get("status") == "SELECT":
            if blind.get("type") == "BOSS":
                return rpc("select")
            score = blind.get("score", 300)
            target, _ = cards_needed_for_score(state)
            jokers = state.get("jokers", {}).get("cards", [])
            if len(jokers) >= 2 or score <= 300:
                return rpc("select")
            if blind.get("type") in ("SMALL", "BIG"):
                return rpc("select")
    return rpc("select")


def handle_selecting_hand(state):
    hand_cards = state["hand"]["cards"]
    if not hand_cards:
        return rpc("play", {"cards": [0]})

    consumable_result = try_use_consumables(state)
    if consumable_result is not None:
        return consumable_result

    best_indices, best_name, best_score = find_best_hand(state)
    target, hands_left = cards_needed_for_score(state)
    round_info = state.get("round", {})
    discards_left = round_info.get("discards_left", 3)

    if best_score * max(hands_left, 1) < target and discards_left > 0:
        discards = choose_discards(state, best_indices, best_name)
        if discards and len(discards) > 0:
            return rpc("discard", {"cards": discards})

    num = min(5, len(best_indices)) if best_indices else 1
    cards = best_indices[:num] if best_indices else [0]
    return rpc("play", {"cards": cards})


def try_use_consumables(state):
    consumables = state.get("consumables", {}).get("cards", [])
    if not consumables:
        return None
    hand_cards = state.get("hand", {}).get("cards", [])
    hand_count = len(hand_cards)

    for i, c in enumerate(consumables):
        key = c.get("key", "")
        if key in PLANET_HAND:
            hand_name = PLANET_HAND[key]
            hands_info = state.get("hands", {})
            if hand_name in hands_info:
                played = hands_info[hand_name].get("played", 0)
                if played > 0:
                    return rpc("use", {"consumable": i})
        elif key in TAROT_ENHANCE:
            _, count = TAROT_ENHANCE[key]
            targets = list(range(min(count, hand_count)))
            if targets:
                return rpc("use", {"consumable": i, "cards": targets})
        elif key in TAROT_SUIT_CONVERT:
            target_suit, count = TAROT_SUIT_CONVERT[key]
            targets = []
            for j, hc in enumerate(hand_cards):
                if get_value(hc, "suit", "H") != target_suit and len(targets) < count:
                    targets.append(j)
            if targets:
                return rpc("use", {"consumable": i, "cards": targets})
        elif key == "c_hermit":
            money = state.get("money", 0)
            if money < 10:
                return rpc("use", {"consumable": i})
        elif key == "c_temperance":
            return rpc("use", {"consumable": i})
        elif key == "c_hanged_man":
            if hand_count > 3:
                worst = []
                for j, hc in enumerate(hand_cards):
                    rank = RANK_ORDER.get(get_value(hc, "rank", "2"), 2)
                    worst.append((rank, j))
                worst.sort()
                targets = [idx for _, idx in worst[:2]]
                return rpc("use", {"consumable": i, "cards": targets})
        elif key == "c_strength":
            targets = list(range(min(2, hand_count)))
            if targets:
                return rpc("use", {"consumable": i, "cards": targets})
        elif key == "c_death":
            if hand_count >= 2:
                best_idx = 0
                best_rank = -1
                for j, hc in enumerate(hand_cards):
                    rank = RANK_ORDER.get(get_value(hc, "rank", "2"), 2)
                    if rank > best_rank:
                        best_rank = rank
                        best_idx = j
                worst_idx = 0
                worst_rank = 999
                for j, hc in enumerate(hand_cards):
                    rank = RANK_ORDER.get(get_value(hc, "rank", "2"), 2)
                    if j != best_idx and rank < worst_rank:
                        worst_rank = rank
                        worst_idx = j
                return rpc("use", {"consumable": i, "cards": [worst_idx, best_idx]})
        elif key == "c_wheel_of_fortune":
            return rpc("use", {"consumable": i})
        elif key == "c_judgement":
            joker_count = state.get("jokers", {}).get("count", 0)
            joker_limit = state.get("jokers", {}).get("limit", 5)
            if joker_count < joker_limit:
                return rpc("use", {"consumable": i})
        elif key in ("c_emperor", "c_high_priestess"):
            return rpc("use", {"consumable": i})
        elif key == "c_fool":
            return None
    return None


def handle_round_eval(state):
    return rpc("cash_out")


def handle_shop(state):
    money = state.get("money", 0)
    shop = state.get("shop", {})
    jokers = state.get("jokers", {}).get("cards", [])
    joker_count = state.get("jokers", {}).get("count", 0)
    joker_limit = state.get("jokers", {}).get("limit", 5)

    if money < 4:
        return rpc("next_round")

    shop_cards = shop.get("cards", [])
    if shop_cards:
        best_buy = None
        best_priority = -1
        best_cost = 999
        best_idx = 0
        for i, sc in enumerate(shop_cards):
            key = sc.get("key", "")
            cost = get_cost(sc, "buy", 0)
            card_set = sc.get("set", "")
            if card_set == "JOKER":
                if joker_count >= joker_limit:
                    lowest_val = None
                    lowest_idx = None
                    for j, jk in enumerate(jokers):
                        if not get_modifier(jk, "eternal", False):
                            val = joker_priority(jk.get("key", ""))
                    sell_val = get_cost(jk, "sell", 1)
                    if lowest_val is None or val < lowest_val or (val == lowest_val and sell_val > get_cost(jk, "sell", 0)):
                                lowest_val = val
                                lowest_idx = j
                    if lowest_idx is not None and joker_priority(key) > lowest_val:
                        if cost - get_cost(jokers[lowest_idx], "sell", 0) <= money:
                            rpc("sell", {"joker": lowest_idx})
                            money = state.get("money", 0)
                            joker_count -= 1
                    elif lowest_idx is None:
                        continue
                if joker_count < joker_limit and cost <= money:
                    pri = joker_priority(key)
                    if has_joker_synergy(key, state):
                        pri += 1
                    if pri > best_priority or (pri == best_priority and cost < best_cost):
                        best_priority = pri
                        best_cost = cost
                        best_buy = "card"
                        best_idx = i

        if best_buy == "card" and money >= best_cost:
            return rpc("buy", {"card": best_idx})

    packs = shop.get("packs", [])
    if packs:
        for i, p in enumerate(packs):
            cost = get_cost(p, "buy", 0)
            if cost <= money - 4:
                key = p.get("key", "")
                if "arcana" in key or "celestial" in key:
                    return rpc("buy", {"pack": i})
        for i, p in enumerate(packs):
            cost = get_cost(p, "buy", 0)
            if cost <= money - 4:
                return rpc("buy", {"pack": i})

    vouchers = shop.get("vouchers", {})
    voucher_cards = vouchers.get("cards", [])
    if voucher_cards:
        for i, v in enumerate(voucher_cards):
            cost = get_cost(v, "buy", 0)
            if cost <= money - 4:
                return rpc("buy", {"voucher": i})

    reroll_cost = state.get("round", {}).get("reroll_cost", 5)
    if money > reroll_cost + 8 and not shop_cards:
        return rpc("reroll")

    return rpc("next_round")


def handle_pack(state):
    pack = state.get("pack", {})
    pack_cards = pack.get("cards", [])

    if not pack_cards:
        return rpc("pack", {"skip": True})

    joker_count = state.get("jokers", {}).get("count", 0)
    joker_limit = state.get("jokers", {}).get("limit", 5)

    for i, pc in enumerate(pack_cards):
        card_set = pc.get("set", "")
        key = pc.get("key", "")

        if card_set == "JOKER":
            if joker_count < joker_limit:
                return rpc("pack", {"card": i})
            return rpc("pack", {"skip": True})

        if card_set == "DEFAULT" or card_set == "ENHANCED":
            return rpc("pack", {"card": i})

        if card_set == "PLANET":
            hand_name = PLANET_HAND.get(key)
            if hand_name:
                hands_info = state.get("hands", {})
                if hands_info.get(hand_name, {}).get("played", 0) > 0:
                    return rpc("pack", {"card": i})
            continue

        if card_set in ("TAROT", "SPECTRAL"):
            if key in TAROT_ENHANCE:
                _, count = TAROT_ENHANCE[key]
                hand_cards = state.get("hand", {}).get("cards", [])
                targets = list(range(min(count, len(hand_cards))))
                if targets:
                    return rpc("pack", {"card": i, "targets": targets})
                continue
            elif key in TAROT_SUIT_CONVERT:
                _, count = TAROT_SUIT_CONVERT[key]
                hand_cards = state.get("hand", {}).get("cards", [])
                targets = []
                for j, hc in enumerate(hand_cards):
                    if len(targets) < count:
                        targets.append(j)
                if targets:
                    return rpc("pack", {"card": i, "targets": targets})
                continue
            elif key in ("c_hermit", "c_temperance", "c_emperor", "c_high_priestess",
                         "c_judgement", "c_wheel_of_fortune", "c_fool"):
                return rpc("pack", {"card": i})
            elif card_set == "SPECTRAL":
                continue
            return rpc("pack", {"card": i})

    return rpc("pack", {"skip": True})


def handle_sell_jokers(state):
    jokers = state.get("jokers", {}).get("cards", [])
    for i, j in enumerate(jokers):
        if get_modifier(j, "rental", False):
            key = j.get("key", "")
            if joker_priority(key) < 2:
                return rpc("sell", {"joker": i})
    return None


def handle_rearrange_jokers(state):
    jokers = state.get("jokers", {}).get("cards", [])
    if len(jokers) <= 1:
        return None
    order = {"chips": 0, "mult": 1, "utility": 2, "xmult": 3}
    def sort_key(j):
        key = j.get("key", "")
        if key in JOKER_XMULT:
            return order["xmult"]
        if key in JOKER_MULT:
            return order["mult"]
        if key in JOKER_CHIPS:
            return order["chips"]
        return order["utility"]
    indices = list(range(len(jokers)))
    indices.sort(key=lambda i: sort_key(jokers[i]))
    current = list(range(len(jokers)))
    if indices == current:
        return None
    return rpc("rearrange", {"jokers": indices})


def play_game():
    state = rpc("gamestate")

    if state.get("state") != "MENU":
        rpc("menu")
        state = rpc("gamestate")

    params = {"deck": DECK, "stake": STAKE}
    if SEED:
        params["seed"] = SEED
    state = rpc("start", params)
    seed = state.get("seed", "???")
    print(f"Started run: deck={DECK}, stake={STAKE}, seed={seed}")

    run_log = {
        "seed": seed,
        "deck": DECK,
        "stake": STAKE,
        "won": False,
        "ante": 0,
        "round": 0,
        "jokers": [],
        "hands_played": Counter(),
        "loss_reason": None,
    }

    while state.get("state") != "GAME_OVER":
        game_state = state.get("state", "")

        match game_state:
            case "BLIND_SELECT":
                state = handle_blind_select(state)

            case "SELECTING_HAND":
                rearranged = handle_rearrange_jokers(state)
                if rearranged is not None:
                    state = rearranged
                if state.get("state") != "SELECTING_HAND":
                    continue
                best_indices, best_name, best_score = find_best_hand(state)
                run_log["hands_played"][best_name] += 1
                state = handle_selecting_hand(state)

            case "ROUND_EVAL":
                state = handle_round_eval(state)

            case "SHOP":
                handle_sell_jokers(state)
                jokers = state.get("jokers", {}).get("cards", [])
                run_log["jokers"] = [j.get("key", "?") for j in jokers]
                state = handle_shop(state)

            case "SMODS_BOOSTER_OPENED":
                state = handle_pack(state)

            case _:
                state = rpc("gamestate")

        run_log["ante"] = state.get("ante_num", run_log["ante"])
        run_log["round"] = state.get("round_num", run_log["round"])

    won = state.get("won", False)
    run_log["won"] = won
    if won:
        print(f"Victory! Final ante: {run_log['ante']}")
    else:
        print(f"Game over at ante {run_log['ante']}, round {run_log['round']}")
        if run_log["ante"] <= 1:
            run_log["loss_reason"] = "early_ante"
        elif run_log["ante"] <= 3:
            run_log["loss_reason"] = "mid_ante"
        elif run_log["ante"] <= 5:
            run_log["loss_reason"] = "late_ante"
        else:
            run_log["loss_reason"] = "endgame"

    return run_log


def generate_report(run_logs, run_num):
    total = len(run_logs)
    wins = sum(1 for r in run_logs if r["won"])
    losses = total - wins
    win_rate = (wins / total * 100) if total > 0 else 0

    ante_deaths = Counter()
    for r in run_logs:
        if not r["won"]:
            ante_deaths[r["ante"]] += 1

    loss_reasons = Counter(r["loss_reason"] for r in run_logs if r["loss_reason"])
    all_hands = Counter()
    for r in run_logs:
        all_hands.update(r["hands_played"])

    joker_counts = Counter()
    for r in run_logs:
        for j in r["jokers"]:
            joker_counts[j] += 1

    print(f"\n{'='*60}")
    print(f"  RUN REPORT  (after {run_num} runs)")
    print(f"{'='*60}")
    print(f"  Total: {total}  |  Wins: {wins}  |  Losses: {losses}  |  Win Rate: {win_rate:.1f}%")
    if ante_deaths:
        print(f"\n  Deaths by Ante:")
        for ante in sorted(ante_deaths):
            label = f"Ante {ante}" if ante > 0 else "Unknown"
            print(f"    {label}: {ante_deaths[ante]}")
    if loss_reasons:
        print(f"\n  Loss Categories:")
        for reason, count in loss_reasons.most_common():
            label = reason.replace("_", " ").title()
            print(f"    {label}: {count}")
    if all_hands:
        print(f"\n  Hands Played (most common):")
        for hand, count in all_hands.most_common(5):
            print(f"    {hand}: {count}")
    if joker_counts:
        print(f"\n  Most Used Jokers:")
        for joker, count in joker_counts.most_common(5):
            print(f"    {joker}: {count}")

    suggestions = []
    if win_rate < 20:
        suggestions.append("Win rate is very low. Consider switching to a stronger deck (PLASMA/BLUE).")
    if win_rate < 50 and "early_ante" in loss_reasons:
        suggestions.append("Frequent early deaths. Prioritize buying +Mult jokers early to survive Ante 1-2.")
    if "mid_ante" in loss_reasons:
        suggestions.append("Dying in mid-antes. Look for X-Mult jokers (Cavendish, Hologram, Baron) and economy.")
    if "late_ante" in loss_reasons:
        suggestions.append("Struggling in late-antes. Need better scaling: Obelisk, Steel Joker, Constellation.")
    if "endgame" in loss_reasons:
        suggestions.append("Close to winning! Focus on glass cards, Red Seal, and X-Mult stacking for Ante 8.")
    top_hand = all_hands.most_common(1)
    if top_hand and top_hand[0][0] in ("High Card", "Pair"):
        suggestions.append("Relying on weak hands. Try to build toward Flush/Full House with suit converters.")
    xmunt_count = sum(count for j, count in joker_counts.items() if j in JOKER_XMULT)
    mult_count = sum(count for j, count in joker_counts.items() if j in JOKER_MULT)
    if mult_count > xmunt_count * 3 and mult_count > 5:
        suggestions.append("Lots of +Mult jokers but few X-Mult. Adding X-Mult dramatically increases score.")

    if suggestions:
        print(f"\n  Suggested Optimizations:")
        for i, s in enumerate(suggestions, 1):
            print(f"    {i}. {s}")
    print(f"{'='*60}\n")


def main():
    if DESIRED_RUNS == 0:
        print(f"DESIRED_RUNS=0: Running infinitely. Press Ctrl+C to stop and get report.")
    else:
        print(f"Running {DESIRED_RUNS} run(s)...")

    run_logs = []
    run_count = 0

    try:
        while True:
            run_count += 1
            print(f"\n--- Run {run_count}{'/' + str(DESIRED_RUNS) if DESIRED_RUNS else ''} ---")
            result = play_game()
            run_logs.append(result)

            if DESIRED_RUNS > 0 and run_count >= DESIRED_RUNS:
                break

            if run_count % 5 == 0:
                generate_report(run_logs, run_count)

    except KeyboardInterrupt:
        print(f"\n\nStopped by user after {run_count} runs.")

    if run_logs:
        generate_report(run_logs, run_count)


if __name__ == "__main__":
    main()
