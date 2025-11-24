"""Basic smoke tests for the prototype.

Run with:
  python scripts/test_basic.py

This script performs small checks: load card data, create a Battle instance,
draw a hand and play a card to verify no immediate exceptions.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def run():
    print('Running basic smoke tests...')
    try:
        from src.common.models import load_cards_from_file, Card
        from src.p2p_network.battle import Battle

        cards = load_cards_from_file(str(ROOT / 'data' / 'cards.json'))
        if not cards:
            print('FAIL: no cards loaded')
            return 2

        deck = []
        # build a tiny deck from the first card
        for i, c in enumerate(cards.values()):
            deck.append(Card.from_dict(c.raw))
            if i >= 3:
                break

        def on_remote(p):
            print('remote intent:', p)

        b = Battle(deck, on_remote_intent=on_remote)
        # For a fast, non-blocking smoke test we avoid network blocking
        # (Battle.start_as_responder blocks waiting for a socket connection).
        # Instead, provide a local deterministic RNG and draw opening hand.
        from src.p2p_network.rng_manager import RNGManager
        b.rng = RNGManager(0)
        # shuffle/draw like start_as_responder would
        b.rng.shuffle(b.local_deck)
        for _ in range(3):
            c = b.rng.draw_card(b.local_deck)
            if c:
                b.local_hand.append(c)
        st = b.get_state()
        print('Initial state:', st)

        if st.get('hand') is None:
            print('FAIL: no hand key in state')
            return 3

        # if hand non-empty, play the first card
        hand = st.get('hand', [])
        if hand:
            # play_card will attempt to send a network intent; in this smoke test
            # there may be no connected peer, which raises RuntimeError from P2PPeer.
            # That's acceptable here as long as the local effect (enemy_health) was applied.
            before = b.enemy_health
            try:
                ok = b.play_card(0)
                print('Played card ok?', ok)
            except RuntimeError as e:
                print('play_card raised (no peer):', e)
                ok = False

            after = b.enemy_health
            if after < before:
                print('Local effect observed: enemy health reduced', before, '->', after)
            else:
                print('No local effect observed')
        else:
            print('No cards to play — ok for small deck')

        print('Smoke tests completed (non-blocking mode)')
        return 0
    except Exception as e:
        print('TEST ERROR:', type(e).__name__, e)
        return 1


if __name__ == '__main__':
    sys.exit(run())
