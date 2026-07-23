import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import ComplaintTable from "../components/ComplaintTable";
import NewComplaintModal from "../components/NewComplaintModal";
import SignalsPanel from "../components/SignalsPanel";
import StatCards from "../components/StatCards";
import {
  cleanParams,
  fetchComplaints,
  fetchSignals,
  fetchStats,
  resetFilters,
  setFilters,
} from "../store/complaintsSlice";

export default function Dashboard() {
  const dispatch = useDispatch();
  const { items, listStatus, filters, total, pages, error } = useSelector((s) => s.complaints);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    dispatch(fetchComplaints(cleanParams(filters)));
    dispatch(fetchStats());
    dispatch(fetchSignals());
  }, [dispatch, filters]);

  function updateFilter(partial) {
    dispatch(setFilters(partial));
  }

  return (
    <div className="main">
      <div className="page-head">
        <div>
          <h1 className="page-title">Customer Complaints</h1>
          <p className="page-subtitle">
            AI assisted intake, triage and CAPA for pharmaceutical quality events
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          + New complaint
        </button>
      </div>

      <StatCards
        onFilter={(partial) => updateFilter(partial)}
      />

      <SignalsPanel />

      <div className="card">
        <div className="card-head filters-head">
          <span>Complaint worklist</span>
          <span className="muted">{total} total</span>
        </div>

        <div className="filters-bar">
          <input
            className="filter-input"
            type="search"
            placeholder="Search reference, product, batch..."
            value={filters.q}
            onChange={(e) => updateFilter({ q: e.target.value, page: 1 })}
          />
          <select
            className="filter-select"
            value={filters.status}
            onChange={(e) => updateFilter({ status: e.target.value, page: 1 })}
          >
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="under_review">Under review</option>
            <option value="closed">Closed</option>
          </select>
          <select
            className="filter-select"
            value={filters.risk_level}
            onChange={(e) => updateFilter({ risk_level: e.target.value, page: 1 })}
          >
            <option value="">All risks</option>
            <option value="Critical">Critical</option>
            <option value="Major">Major</option>
            <option value="Minor">Minor</option>
          </select>
          <select
            className="filter-select"
            value={filters.reportable}
            onChange={(e) => updateFilter({ reportable: e.target.value, page: 1 })}
          >
            <option value="">Reportable: any</option>
            <option value="true">Reportable only</option>
            <option value="false">Not reportable</option>
          </select>
          <select
            className="filter-select"
            value={filters.overdue}
            onChange={(e) => updateFilter({ overdue: e.target.value, page: 1 })}
          >
            <option value="">SLA: any</option>
            <option value="true">Overdue only</option>
            <option value="false">On track</option>
          </select>
          <select
            className="filter-select"
            value={`${filters.sort}:${filters.order}`}
            onChange={(e) => {
              const [sort, order] = e.target.value.split(":");
              updateFilter({ sort, order, page: 1 });
            }}
          >
            <option value="created_at:desc">Newest first</option>
            <option value="created_at:asc">Oldest first</option>
            <option value="reference:asc">Reference A-Z</option>
            <option value="risk_level:desc">Risk</option>
            <option value="status:asc">Status</option>
          </select>
          <button className="btn btn-ghost" type="button" onClick={() => dispatch(resetFilters())}>
            Reset
          </button>
        </div>

        {error && listStatus === "failed" && (
          <div className="error-text" style={{ padding: "12px 16px" }}>
            Could not load complaints: {error}. Is the backend running?
          </div>
        )}

        <ComplaintTable items={items} loading={listStatus === "loading"} />

        {pages > 1 && (
          <div className="pagination">
            <button
              className="btn btn-ghost"
              disabled={filters.page <= 1}
              onClick={() => updateFilter({ page: filters.page - 1 })}
            >
              Previous
            </button>
            <span className="muted">
              Page {filters.page} of {pages}
            </span>
            <button
              className="btn btn-ghost"
              disabled={filters.page >= pages}
              onClick={() => updateFilter({ page: filters.page + 1 })}
            >
              Next
            </button>
          </div>
        )}
      </div>

      {showModal && <NewComplaintModal onClose={() => setShowModal(false)} />}
    </div>
  );
}
