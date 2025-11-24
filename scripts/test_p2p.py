"""A tiny manual test script for P2P handshake and simple play between two local processes.

Usage:
  - Run this script twice on the same machine.
  - First instance: python scripts/test_p2p.py --listen 6001
  - Second instance: python scripts/test_p2p.py --connect 127.0.0.1:6001

This is a minimal demonstration and uses `data/cards.json` to populate decks.
"""
import argparse
import json
import time
from pathlib import Path

from src.common.models import load_cards_from_file, Card
from src.p2p_network.battle import Battle


def load_deck_sample():
    cards = load_cards_from_file(str(Path(__file__).resolve().parents[1] / 'data' / 'cards.json'))
    # simple deck: 5 copies of each sample card
    deck = []
    for i in range(5):
        for c in cards.values():
            deck.append(Card.from_dict(c.raw))
    return deck


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--listen', type=int, help='listen port to accept a peer')
    p.add_argument('--connect', type=str, help='peer ip:port to connect to')
    args = p.parse_args()

    deck = load_deck_sample()
    b = Battle(deck, on_remote_intent=lambda x: print('remote intent', x))

    if args.listen:
        print('Listening on', args.listen)
        b.start_as_responder(args.listen)
        print('Responder ready. State:', b.get_state())
    elif args.connect:
        ip, port = args.connect.split(':')
        print('Connecting to', ip, port)
        b.start_as_initiator(ip, int(port))
        print('Initiator ready. State:', b.get_state())
        # play first card
        time.sleep(0.5)
        if b.local_hand:
            print('Playing a card', b.local_hand[0].to_dict())
            b.play_card(0)
            print('State after play:', b.get_state())


if __name__ == '__main__':
    main()
