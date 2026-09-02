def discover_candidates(
    target_count=12,
):
    """
    Sequence:

    1. Find current market dislocations.
    2. Rank every security with a qualifying discovery signal.
    3. Evaluate eligibility for the entire ranked pool.
    4. Record every eligibility decision.
    5. Freeze only the first target_count eligible securities.

    The audit continues after the frozen list is complete.
    """

    ranked_pool = (
        build_ranked_dislocation_pool()
    )

    frozen_candidates = []
    eligibility_audit = []

    for discovery_rank, item in enumerate(
        ranked_pool,
        start=1,
    ):

        ticker = item[
            "ticker"
        ]

        eligibility = evaluate_eligibility(
            ticker
        )

        entry_reason = build_entry_reason(
            item["signals"]
        )

        eligibility_audit.append(
            EligibilityAuditItem(
                discovery_rank=discovery_rank,
                ticker=ticker,
                company=item["company"],
                discovery_score=item["score"],
                entry_reason=entry_reason,
                eligibility_status=eligibility.status,
                eligible=eligibility.eligible,
                eligibility_reason=eligibility.reason,
                security_type=eligibility.security_type,
                market_cap=eligibility.market_cap,
                profitable=eligibility.profitable,
                net_income=eligibility.net_income,
                eligibility_source=eligibility.source,
                eligibility_retrieved_at=eligibility.retrieved_at,
            )
        )

        # The audit keeps running for every discovery candidate.
        # Only the frozen list stops growing after target_count.

        if (
            eligibility.eligible
            and len(frozen_candidates) < target_count
        ):

            metrics = item[
                "metrics"
            ]

            frozen_candidates.append(
                DiscoveredCandidate(
                    ticker=ticker,
                    company=item["company"],
                    entry_reason=entry_reason,

                    last_price=metrics[
                        "last_price"
                    ],

                    return_1d=metrics[
                        "return_1d"
                    ],

                    return_1m=metrics[
                        "return_1m"
                    ],

                    return_3m=metrics[
                        "return_3m"
                    ],

                    return_6m=metrics[
                        "return_6m"
                    ],

                    drawdown_from_52w_high=(
                        metrics[
                            "drawdown_from_52w_high"
                        ]
                    ),

                    distance_from_52w_low=(
                        metrics[
                            "distance_from_52w_low"
                        ]
                    ),

                    volume_ratio=metrics[
                        "volume_ratio"
                    ],

                    discovery_score=item[
                        "score"
                    ],

                    eligibility_status=(
                        eligibility.status
                    ),

                    eligibility_reason=(
                        eligibility.reason
                    ),

                    market_cap=(
                        eligibility.market_cap
                    ),

                    profitable=(
                        eligibility.profitable
                    ),

                    discovery_source=(
                        "Yahoo Finance daily market data; "
                        "S&P 500 constituents retrieved with "
                        "requests and parsed locally; eligibility "
                        "evaluated before final candidate freeze"
                    ),

                    retrieved_at=item[
                        "retrieved_at"
                    ],

                    signals=item[
                        "signals"
                    ],
                )
            )

    return (
        frozen_candidates,
        eligibility_audit,
    )
