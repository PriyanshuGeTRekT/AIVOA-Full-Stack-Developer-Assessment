import { configureStore } from "@reduxjs/toolkit";

import complaintsReducer from "./complaintsSlice";

export const store = configureStore({
  reducer: {
    complaints: complaintsReducer,
  },
});
