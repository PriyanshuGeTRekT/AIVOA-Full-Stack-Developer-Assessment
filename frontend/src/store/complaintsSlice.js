import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import { complaintsApi, waitForProcessing } from "../api/client";

export const fetchComplaints = createAsyncThunk(
  "complaints/fetchAll",
  (params = {}, { getState }) => {
    const filters = params && Object.keys(params).length
      ? params
      : getState().complaints.filters;
    return complaintsApi.list(filters);
  }
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

async function createAndWait(createFn, payload) {
  const created = await createFn(payload);
  if (created.processing_state === "done" || created.processing_state === "failed") {
    return created;
  }
  return waitForProcessing(created.id);
}

export const submitTextComplaint = createAsyncThunk(
  "complaints/submitText",
  (text) => createAndWait(complaintsApi.createFromText, text)
);

export const submitFileComplaint = createAsyncThunk(
  "complaints/submitFile",
  (file) => createAndWait(complaintsApi.createFromFile, file)
);

export const changeStatus = createAsyncThunk(
  "complaints/changeStatus",
  async ({ id, status }, { rejectWithValue }) => {
    try {
      return await complaintsApi.updateStatus(id, status);
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message;
      return rejectWithValue(detail);
    }
  }
);

export const reprocessComplaint = createAsyncThunk(
  "complaints/reprocess",
  async (id) => {
    const started = await complaintsApi.reprocess(id);
    if (started.processing_state === "done" || started.processing_state === "failed") {
      return started;
    }
    return waitForProcessing(id);
  }
);

export const overrideRisk = createAsyncThunk(
  "complaints/overrideRisk",
  ({ id, risk_level, reason, actor }) =>
    complaintsApi.overrideRisk(id, risk_level, reason, actor)
);

const defaultFilters = {
  q: "",
  status: "",
  risk_level: "",
  reportable: "",
  overdue: "",
  sort: "created_at",
  order: "desc",
  page: 1,
  page_size: 50,
};

const initialState = {
  items: [],
  total: 0,
  pages: 1,
  filters: { ...defaultFilters },
  stats: {
    total: 0, open: 0, under_review: 0, closed: 0,
    critical: 0, major: 0, minor: 0, reportable: 0, overdue: 0, processing: 0,
  },
  signals: [],
  selected: null,
  listStatus: "idle",
  submitStatus: "idle",
  error: null,
};

function cleanParams(filters) {
  const params = {};
  Object.entries(filters).forEach(([key, value]) => {
    if (value === "" || value === null || value === undefined) return;
    params[key] = value;
  });
  return params;
}

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
    setFilters(state, action) {
      state.filters = {
        ...state.filters,
        ...action.payload,
        page: action.payload.page ?? 1,
      };
    },
    resetFilters(state) {
      state.filters = { ...defaultFilters };
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchComplaints.pending, (state) => {
        state.listStatus = "loading";
      })
      .addCase(fetchComplaints.fulfilled, (state, action) => {
        state.listStatus = "succeeded";
        state.items = action.payload.items || [];
        state.total = action.payload.total ?? 0;
        state.pages = action.payload.pages ?? 1;
      })
      .addCase(fetchComplaints.rejected, (state, action) => {
        state.listStatus = "failed";
        state.error = action.error.message;
      })
      .addCase(fetchStats.fulfilled, (state, action) => {
        state.stats = { ...state.stats, ...action.payload };
      })
      .addCase(fetchSignals.fulfilled, (state, action) => {
        state.signals = action.payload;
      })
      .addCase(fetchComplaint.fulfilled, (state, action) => {
        state.selected = action.payload;
      })
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
        state.total += 1;
      })
      .addCase(submitFileComplaint.fulfilled, (state, action) => {
        state.submitStatus = "succeeded";
        state.items.unshift(toRow(action.payload));
        state.selected = action.payload;
        state.total += 1;
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
        state.error = null;
      })
      .addCase(changeStatus.rejected, (state, action) => {
        state.error = action.payload || action.error.message;
      })
      .addCase(reprocessComplaint.fulfilled, (state, action) => {
        applyUpdate(state, action.payload);
      })
      .addCase(overrideRisk.fulfilled, (state, action) => {
        applyUpdate(state, action.payload);
      });
  },
});

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

function applyUpdate(state, updated) {
  state.selected = updated;
  const index = state.items.findIndex((c) => c.id === updated.id);
  if (index !== -1) {
    state.items[index] = toRow(updated);
  }
}

export const { clearSelected, clearSubmitStatus, setFilters, resetFilters } =
  complaintsSlice.actions;
export { cleanParams, defaultFilters };
export default complaintsSlice.reducer;
