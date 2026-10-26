# PRD 23 acceptance trace

Generated 2026-10-26 19:25 by `scripts/acceptance.py`. 44/44 tests passed; 30/36 TC ids pass by automated test (synthetic fixtures + test-only mock backend for model output).

| TC | Scenario | Status | Evidence |
|---|---|---|---|
| TC-001 | Minimal closed loop | pass | test_end_to_end_api_TC001, test_closed_loop_TC001_and_originals_unchanged_TC024 |
| TC-002 | Empty library cannot claim missing | pass | test_empty_library_is_not_a_gap_TC002 |
| TC-003 | Pending assets protect the verdict | pass | test_pending_assets_protect_gap_conclusion_TC003 |
| TC-004 | Decode failure is not absence | pass | test_failed_file_is_not_absence_TC004_and_duplicates_TC013, test_decode_failure_is_not_absence_TC004 |
| TC-005 | Similar but too short | pass | test_similar_but_too_short_is_partial_TC005 |
| TC-006 | Not at the same time is not same frame | pass | test_cooccurrence_needs_same_time_TC006 |
| TC-007 | One frame cannot prove an action | pass | test_single_frame_cannot_prove_action_TC007 |
| TC-008 | Unknown is never pass | pass | test_three_valued_logic_TC008 |
| TC-009 | Normal empty result | pass | test_no_results_no_fake_timecodes_TC009 |
| TC-010 | Requirement edit invalidates old results | pass | test_requirement_change_marks_outdated_TC010_and_409_TC036, test_revision_change_invalidates_human_confirmation_TC010 |
| TC-011 | Denominator keeps unknown requirements | pass | test_denominator_keeps_unknowns_TC011 |
| TC-012 | Two segments cannot be added up | pass | test_two_short_pieces_do_not_add_up_TC012 |
| TC-013 | Duplicate file is not two takes | pass | test_failed_file_is_not_absence_TC004_and_duplicates_TC013, test_duplicate_is_not_two_takes_TC013 |
| TC-014 | Original timeline and rotation | pass | test_rotation_and_timeline_TC014 |
| TC-015 | Detector boxes mapped back to the frame | not_applicable | no object detector in v1 (MODEL_PLAN: planned for Stage II) |
| TC-016 | Incompatible model vectors | pass | test_model_mismatch_TC016_and_cache_invalidation_TC030 |
| TC-017 | Quantization quality comparison | not_run | needs a real UGen300 run (G1 gate) |
| TC-018 | Device unplugged and fallback | partial | test_device_status_never_claims_npu_TC018 (backend label never claims NPU; the unplug-during-run test needs a UGen300) |
| TC-019 | Core flow offline | pass | test_core_flow_makes_no_outbound_connection_TC019 |
| TC-020 | Malicious text and paths | pass | test_token_and_origin_required_TC020, test_html_report_escapes_text_TC020, test_paths_must_stay_inside_root_TC020 |
| TC-021 | CSV formula injection | pass | test_csv_formula_injection_TC021 |
| TC-022 | Interrupted job and recovery | pass | test_resume_after_interruption_TC022 |
| TC-023 | Disk full | pass | test_disk_full_stops_safely_and_recovers_TC023 |
| TC-024 | Originals untouched | pass | test_closed_loop_TC001_and_originals_unchanged_TC024 |
| TC-025 | Manual exception traceable | pass | test_exception_is_traceable_TC025 |
| TC-026 | Manually found segment | pass | test_manual_segment_counts_for_human_only_TC026 |
| TC-027 | Reshoot cards are not invented | pass | test_reshoot_cards_only_confirmed_and_review_first_TC027 |
| TC-028 | New clip does not recompute old ones | pass | test_incremental_analysis_TC028 |
| TC-029 | File still being written | pass | test_file_still_being_written_TC029 |
| TC-030 | Model update and cache invalidation | pass | test_model_mismatch_TC016_and_cache_invalidation_TC030 |
| TC-031 | Report and relocation | pass | test_moved_file_is_missing_then_relocated_by_hash_TC031 |
| TC-032 | Search latency under load | measured | eval/results/perf.json: p50/p95 over 10,000 segments, text encoded per query (no cached answers) |
| TC-033 | Editing on the same machine | proxy | eval/results/interference.json: playback proxy, not an NLE; UGen300 not_run |
| TC-034 | Accessibility and status understanding | manual_check | UI uses icon + text for every status (docs/ui_preview); no user test yet |
| TC-035 | Clean environment rebuild | pass | fresh venv (3.13.9, Windows-11-10.0.26200-SP0) at 2026-10-26 18:23:34: 44 passed, 1 warning in 11.33s (scripts/clean_env.sh) |
| TC-036 | Validity version conflict | pass | test_requirement_change_marks_outdated_TC010_and_409_TC036 |
