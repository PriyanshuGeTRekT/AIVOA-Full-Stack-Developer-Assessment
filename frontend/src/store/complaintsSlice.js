import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import { complaintsApi } from "../api/client";

// All server interaction goes through async thunks so components stay free of
// data fetching logic and the loading/error state lives in one predictable
// place. This is the standard Redux Toolkit pattern.

export const fetchComplaints = createAsyncThunk("complaints/fetchAll", () =>
  complaintsApi.list()
);

export const fetchStats = createAsyncThunk("complaints/fetchStats", () =>
  complaintsApi.stats()
);

export const fetchSignals = createAsyncThunk("complaints/fetchSignals", () =>
  complaintsApi.signals()
);

export const fetchComplaint = createAsyncThunk("complaints/fetchOne", (id) =>
  complaintsApi.get(id)
);

export const submitTextComplaint = createAsyncThunk(
  "complaints/submitText",
  (text) => complaintsApi.createFromText(text)
);

export const submitFileComplaint = createAsyncThunk(
  "complaints/submitFile",
  (file) => complaintsApi.createFromFile(file)
);

export const changeStatus = createAsyncThunk(
  "complaints/changeStatus",
  ({ id, status }) => complaintsApi.updateStatus(id, status)
);

export const reprocessComplaint = createAsyncThunk(
  "complaints/reprocess",
  (id) => complaintsApi.reprocess(id)
);

export const overrideRisk = createAsyncThunk(
  "complaints/overrideRisk",
  ({ id, risk_level, reason, actor }) =>
    complaintsApi.overrideRisk(id, risk_level, reason, actor)
);

const initialState = {
  items: [],
  stats: {
    total: 0, open: 0, under_review: 0, closed: 0,
    critical: 0, major: 0, minor: 0, reportable: 0, overdue: 0,
  },
  signals: [],
  selected: null,
  listStatus: "idle",
  submitStatus: "idle",
  error: null,
};

const complaintsSlice = createSlice({
  name: "complaints",
  initialState,
  reducers: {
    clearSelected(state) {
      state.selected = null;
    },
    clearSubmitStatus(state) {
      state.submitStatus = "idle";
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchComplaints.pending, (state) => {
        state.listStatus = "loading";
      })
      .addCase(fetchComplaints.fulfilled, (state, action) => {
        state.listStatus = "succeeded";
        state.items = action.payload;
      })
      .addCase(fetchComplaints.rejected, (state, action) => {
        state.listStatus = "failed";
        state.error = action.error.message;
      })
      .addCase(fetchStats.fulfilled, (state, action) => {
        state.stats = action.payload;
      })
      .addCase(fetchSignals.fulfilled, (state, action) => {
        state.signals = action.payload;
      })
      .addCase(fetchComplaint.fulfilled, (state, action) => {
        state.selected = action.payload;
      })
      // Both intake paths behave the same way from the UI's point of view.
      .addCase(submitTextComplaint.pending, (state) => {
        state.submitStatus = "loading";
        state.error = null;
      })
      .addCase(submitFileComplaint.pending, (state) => {
        state.submitStatus = "loading";
        state.error = null;
      })
      .addCase(submitTextComplaint.fulfilled, (state, action) => {
        state.submitStatus = "succeeded";
        state.items.unshift(toRow(action.payload));
        state.selected = action.payload;
      })
      .addCase(submitFileComplaint.fulfilled, (state, action) => {
        state.submitStatus = "succeeded";
        state.items.unshift(toRow(action.payload));
        state.selected = action.payload;
      })
      .addCase(submitTextComplaint.rejected, (state, action) => {
        state.submitStatus = "failed";
        state.error = action.error.message;
      })
      .addCase(submitFileComplaint.rejected, (state, action) => {
        state.submitStatus = "failed";
        state.error = action.error.message;
      })
      .addCase(changeStatus.fulfilled, (state, action) => {
        applyUpdate(state, action.payload);
      })
      .addCase(reprocessComplaint.fulfilled, (state, action) => {
        applyUpdate(state, action.payload);
      })
      .addCase(overrideRisk.fulfilled, (state, action) => {
        applyUpdate(state, action.payload);
      });
  },
});

// Map a full complaint record down to the fields the table row needs.
function toRow(c) {
  return {
    id: c.id,
    reference: c.reference,
    product_name: c.product_name,
    batch_number: c.batch_number,
    complaint_type: c.complaint_type,
    risk_level: c.risk_level,
    reportable: c.reportable,
    status: c.status,
    processing_state: c.processing_state,
    investigation_days_left: c.investigation_days_left,
    is_overdue: c.is_overdue,
    created_at: c.created_at,
  };
}

// Keep the list row and the selected record in sync after an update.
function applyUpdate(state, updated) {
  state.selected = updated;
  const index = state.items.findIndex((c) => c.id === updated.id);
  if (index !== -1) {
    state.items[index] = toRow(updated);
  }
}

export const { clearSelected, clearSubmitStatus } = complaintsSlice.actions;
export default complaintsSlice.reducer;
