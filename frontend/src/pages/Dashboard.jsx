import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import ComplaintTable from "../components/ComplaintTable";
import NewComplaintModal from "../components/NewComplaintModal";
import StatCards from "../components/StatCards";
import { fetchComplaints, fetchStats } from "../store/complaintsSlice";

export default function Dashboard() {
  const dispatch = useDispatch();
  const { items, listStatus } = useSelector((s) => s.complaints);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    dispatch(fetchComplaints());
    dispatch(fetchStats());
  }, [dispatch]);

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

      <StatCards />

      <div className="card">
        <div className="card-head">Complaint worklist</div>
        <ComplaintTable items={items} loading={listStatus === "loading"} />
      </div>

      {showModal && <NewComplaintModal onClose={() => setShowModal(false)} />}
    </div>
  );
}
