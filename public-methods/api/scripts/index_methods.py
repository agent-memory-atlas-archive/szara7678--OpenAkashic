#!/usr/bin/env python3
"""Build the external method index using a fixed local embedding service."""
import argparse
import json
from app.research_method_search import SearchConfig, HTTPEmbedder, build_index
from app.research_method_store import MethodStore
from app.research_store import ResearchStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, help="existing initialized public archive")
    parser.add_argument("--index", required=True, help="external index SQLite path, outside Git")
    parser.add_argument("--endpoint", help="operator-selected loopback HTTP /embed service")
    parser.add_argument("--model")
    parser.add_argument("--revision")
    parser.add_argument("--embedding-spec")
    args = parser.parse_args()
    env = SearchConfig.from_env()
    config = SearchConfig(model=args.model or env.model, revision=args.revision or env.revision,
                          embedding_spec=args.embedding_spec or env.embedding_spec,
                          situation_floor=env.situation_floor, goal_floor=env.goal_floor)
    store = MethodStore(ResearchStore(args.archive, read_only=True))
    result = build_index(store, args.index, HTTPEmbedder(config, args.endpoint), config)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
