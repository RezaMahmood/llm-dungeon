# Azure Portal Dashboard (Microsoft.Portal/dashboards) surfacing failures,
# performance, a top-N slow/failing dependency summary, user statistics (all
# read live from the existing Application Insights / Log Analytics resources
# in monitoring.tf), plus a pinned Azure Monitor Workbook showing a single
# aggregate estimated cost for the Resource Group (data-model.md's Dashboard
# Definition and Resource Group Cost Estimate entities). No new compute,
# pipeline, or access-control resource — see research.md §1-6.
#
# `local.dashboard_parts` is built up one entry per panel, in priority order
# (P1 Failures -> P2 Performance/Traces -> P3 User Statistics -> P4 Cost),
# then merged into the dashboard's `dashboard_properties` JSON document below.
# Every `terraform apply` submits the whole document — there is no
# partial/merge update path, so a redeploy never leaves orphaned panels
# (contracts/dashboard-contract.md's "Replace semantics").

locals {
  # The dashboard's refreshInterval below is set to 5 minutes (FR-012),
  # applying to the Failure/Performance/User-Statistics parts; the Cost
  # panel is a pinned Workbook and refreshes on open instead (research.md §4).
  dashboard_default_timespan_ms = 86400000 # 24h, FR-002/FR-003/FR-005 default window (FR-010)

  # --- User Story 1 (P1): Failures ---
  dashboard_parts_us1 = {
    "0" = {
      position = { x = 0, y = 0, rowSpan = 4, colSpan = 6 }
      metadata = {
        inputs = [
          {
            name = "options"
            value = {
              chart = {
                metrics = [
                  {
                    resourceMetadata = { id = azurerm_application_insights.appinsights.id }
                    name             = "requests/failed"
                    aggregationType  = 5 # Total (Sum) - failed request count over the window
                    namespace        = "microsoft.insights/components"
                    metricVisualization = {
                      displayName = "Failed requests"
                    }
                  }
                ]
                title     = "Failed requests (last 24h)"
                titleKind = 2
                visualization = {
                  chartType           = 2 # Line
                  disablePinning      = true
                  legendVisualization = { isVisible = true, position = 2, hideSubtitle = false }
                  axisVisualization   = { x = { isVisible = true, axisType = 2 }, y = { isVisible = true, axisType = 1 } }
                }
                timespan = {
                  relative    = { duration = local.dashboard_default_timespan_ms }
                  showUTCTime = false
                  grain       = 1
                }
              }
            }
          },
          { name = "sharedTimeRange", isOptional = true }
        ]
        type     = "Extension/HubsExtension/PartType/MonitorChartPart"
        settings = {}
      }
    }
    "1" = {
      position = { x = 6, y = 0, rowSpan = 4, colSpan = 6 }
      metadata = {
        inputs = [
          {
            name = "options"
            value = {
              chart = {
                metrics = [
                  {
                    resourceMetadata = { id = azurerm_application_insights.appinsights.id }
                    name             = "exceptions/count"
                    aggregationType  = 5 # Total (Sum)
                    namespace        = "microsoft.insights/components"
                    metricVisualization = {
                      displayName = "Exceptions"
                    }
                  }
                ]
                title     = "Exceptions (last 24h)"
                titleKind = 2
                visualization = {
                  chartType           = 2
                  disablePinning      = true
                  legendVisualization = { isVisible = true, position = 2, hideSubtitle = false }
                  axisVisualization   = { x = { isVisible = true, axisType = 2 }, y = { isVisible = true, axisType = 1 } }
                }
                timespan = {
                  relative    = { duration = local.dashboard_default_timespan_ms }
                  showUTCTime = false
                  grain       = 1
                }
              }
            }
          },
          { name = "sharedTimeRange", isOptional = true }
        ]
        type     = "Extension/HubsExtension/PartType/MonitorChartPart"
        settings = {}
      }
    }
  }

  # --- User Story 2 (P2): Performance & Traces ---
  dashboard_parts_us2 = {
    "2" = {
      position = { x = 0, y = 4, rowSpan = 4, colSpan = 6 }
      metadata = {
        inputs = [
          {
            name = "options"
            value = {
              chart = {
                metrics = [
                  {
                    resourceMetadata = { id = azurerm_application_insights.appinsights.id }
                    name             = "requests/duration"
                    aggregationType  = 1 # Average
                    namespace        = "microsoft.insights/components"
                    metricVisualization = {
                      displayName = "Response time (avg)"
                    }
                  }
                ]
                title     = "Response time (last 24h)"
                titleKind = 2
                visualization = {
                  chartType           = 2
                  disablePinning      = true
                  legendVisualization = { isVisible = true, position = 2, hideSubtitle = false }
                  axisVisualization   = { x = { isVisible = true, axisType = 2 }, y = { isVisible = true, axisType = 1 } }
                }
                timespan = {
                  relative    = { duration = local.dashboard_default_timespan_ms }
                  showUTCTime = false
                  grain       = 1
                }
              }
            }
          },
          { name = "sharedTimeRange", isOptional = true }
        ]
        type     = "Extension/HubsExtension/PartType/MonitorChartPart"
        settings = {}
      }
    }
    "3" = {
      position = { x = 6, y = 4, rowSpan = 4, colSpan = 6 }
      metadata = {
        inputs = [
          {
            name = "options"
            value = {
              chart = {
                metrics = [
                  {
                    resourceMetadata = { id = azurerm_application_insights.appinsights.id }
                    name             = "requests/count"
                    aggregationType  = 5 # Total (Sum) - throughput over the window
                    namespace        = "microsoft.insights/components"
                    metricVisualization = {
                      displayName = "Throughput (requests)"
                    }
                  }
                ]
                title     = "Throughput (last 24h)"
                titleKind = 2
                visualization = {
                  chartType           = 2
                  disablePinning      = true
                  legendVisualization = { isVisible = true, position = 2, hideSubtitle = false }
                  axisVisualization   = { x = { isVisible = true, axisType = 2 }, y = { isVisible = true, axisType = 1 } }
                }
                timespan = {
                  relative    = { duration = local.dashboard_default_timespan_ms }
                  showUTCTime = false
                  grain       = 1
                }
              }
            }
          },
          { name = "sharedTimeRange", isOptional = true }
        ]
        type     = "Extension/HubsExtension/PartType/MonitorChartPart"
        settings = {}
      }
    }
    # Top-N slowest/failing dependency summary over the window, rendered as a
    # table, with a link out to Application Insights for full trace details
    # (FR-004; data-model.md's Trace/Dependency Record entity). Deliberately a
    # summary, not a full trace explorer, per the spec's clarification.
    "4" = {
      position = { x = 0, y = 8, rowSpan = 4, colSpan = 12 }
      metadata = {
        inputs = [
          { name = "resourceTypeMode", isOptional = true },
          {
            name  = "ComponentId"
            value = { Type = "workspace", ResourceId = azurerm_log_analytics_workspace.logs.id }
          },
          {
            name  = "Query"
            value = <<-KQL
              let base = dependencies
                | where timestamp > ago(24h)
                | summarize AvgDuration = avg(duration), FailureCount = countif(success == false), CallCount = count() by name, target;
              base
              | top 5 by AvgDuration desc
              | union (base | top 5 by FailureCount desc)
              | distinct name, target, AvgDuration, FailureCount, CallCount
              | order by FailureCount desc, AvgDuration desc
            KQL
          },
          { name = "TimeRange", value = "P1D" },
          { name = "ControlType", value = "AnalyticsGrid" },
          { name = "SpecificChart", value = "Table" },
          { name = "PartTitle", value = "Top slow/failing dependencies (last 24h)" },
          { name = "PartSubTitle", value = azurerm_log_analytics_workspace.logs.name },
          {
            name  = "Dimensions"
            value = { xAxis = { name = "name", type = "string" }, yAxis = [{ name = "AvgDuration", type = "real" }], splitBy = [], aggregation = "Sum" }
          },
          { name = "resourceIds", value = [azurerm_application_insights.appinsights.id] },
          { name = "isQueryContainTimeRange", value = true }
        ]
        type = "Extension/HubsExtension/PartType/LogsDashboardPart"
        settings = {
          content = {
            PartTitle    = "Top slow/failing dependencies (last 24h)"
            PartSubTitle = "Summarized from Application Insights - open in Application Insights below for full trace details"
          }
        }
      }
    }
    # Link-out part satisfying FR-004's "link to the corresponding
    # Application Insights trace details" - a stable deep link to the App
    # Insights resource overview, from which Transaction Search is one click
    # away (the exact Transaction Search sub-blade route is not a stable
    # public contract to hardcode).
    "5" = {
      position = { x = 0, y = 12, rowSpan = 1, colSpan = 12 }
      metadata = {
        inputs = []
        type   = "Extension/HubsExtension/PartType/MarkdownPart"
        settings = {
          content = {
            settings = {
              content  = "[Open Application Insights -> Transaction search](https://portal.azure.com/#resource${azurerm_application_insights.appinsights.id}/overview) for full trace details behind the dependency summary above."
              title    = ""
              subtitle = ""
            }
          }
        }
      }
    }
  }

  # --- User Story 3 (P3): User Statistics ---
  dashboard_parts_us3 = {
    "6" = {
      position = { x = 0, y = 13, rowSpan = 4, colSpan = 12 }
      metadata = {
        inputs = [
          { name = "resourceTypeMode", isOptional = true },
          {
            name  = "ComponentId"
            value = { Type = "workspace", ResourceId = azurerm_log_analytics_workspace.logs.id }
          },
          {
            name  = "Query"
            value = <<-KQL
              union customEvents, pageViews
              | where timestamp > ago(24h)
              | summarize Users = dcount(user_Id), Sessions = dcount(session_Id) by bin(timestamp, 1h)
              | order by timestamp asc
            KQL
          },
          { name = "TimeRange", value = "P1D" },
          { name = "ControlType", value = "FrameControlChart" },
          { name = "SpecificChart", value = "Line" },
          { name = "PartTitle", value = "User statistics (last 24h)" },
          { name = "PartSubTitle", value = "Active users and sessions, bucketed hourly" },
          {
            name = "Dimensions"
            value = {
              xAxis       = { name = "timestamp", type = "datetime" }
              yAxis       = [{ name = "Users", type = "long" }, { name = "Sessions", type = "long" }]
              splitBy     = []
              aggregation = "Sum"
            }
          },
          { name = "isQueryContainTimeRange", value = true }
        ]
        type = "Extension/HubsExtension/PartType/LogsDashboardPart"
        settings = {
          content = {
            PartTitle    = "User statistics (last 24h)"
            PartSubTitle = "Active users and sessions, bucketed hourly"
          }
        }
      }
    }
  }

  # --- User Story 4 (P4): Resource Group Cost Estimate ---
  # Not subject to the 5-minute refresh above - a pinned Workbook refreshes
  # on open, matching Cost Management's own (roughly daily) update cadence
  # (research.md §4).
  dashboard_parts_us4 = {
    "7" = {
      position = { x = 0, y = 17, rowSpan = 4, colSpan = 6 }
      metadata = {
        inputs = [
          { name = "ComponentId", value = data.azurerm_resource_group.rg.id },
          { name = "Scope", value = { resourceIds = [data.azurerm_resource_group.rg.id] } },
          {
            name  = "PartId"
            value = azurerm_application_insights_workbook.cost_estimate.name
          }
        ]
        type = "Extension/AppInsightsExtension/PartType/WorkbookPinnedPart"
        settings = {
          content = {
            GalleryId  = "workbook-resource-group-cost-estimate"
            Id         = azurerm_application_insights_workbook.cost_estimate.id
            Type       = "workbook"
            ViewerMode = false
          }
        }
      }
    }
  }

  # Merge every user story's parts into one map - each phase only adds keys,
  # never edits another phase's entry (tasks.md Phase 2 note).
  dashboard_parts = merge(
    local.dashboard_parts_us1,
    local.dashboard_parts_us2,
    local.dashboard_parts_us3,
    local.dashboard_parts_us4,
  )
}

resource "azurerm_portal_dashboard" "dashboard" {
  name                = local.dashboard_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  tags                = local.common_tags

  dashboard_properties = jsonencode({
    lenses = {
      "0" = {
        order = 0
        parts = local.dashboard_parts
      }
    }
    metadata = {
      model = {
        timeRange = {
          value = { relative = { duration = local.dashboard_default_timespan_ms } }
          type  = "MsPortalFx.Composition.Configuration.ValueTypes.TimeRange"
        }
        # Portal-native auto-refresh, in minutes - satisfies FR-012 for the
        # Failure/Performance/User-Statistics parts above without any custom
        # polling code (research.md §2).
        refreshInterval = "PT5M"
      }
    }
  })
}

# Azure Monitor Workbook holding the Resource Group's single aggregate
# estimated cost (data-model.md's Resource Group Cost Estimate entity). The
# `name` argument is a GUID identifying this Workbook instance (an Azure ARM
# requirement for this resource type, not a Terraform choice) - `uuidv5`
# keeps it stable across applies without introducing a `random` provider
# dependency for a single deterministic value (research.md §1's "no new
# provider" decision).
resource "azurerm_application_insights_workbook" "cost_estimate" {
  name                = uuidv5("dns", "${local.dashboard_name}-cost-estimate-workbook")
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  display_name        = "${local.dashboard_name}-cost-estimate"
  # The provider validates source_id has no uppercase letters, but Azure
  # resource IDs always contain "resourceGroups" - lowercase it to satisfy
  # that check without changing which resource it actually points to.
  source_id = lower(data.azurerm_resource_group.rg.id)
  tags      = local.common_tags

  data_json = jsonencode({
    version = "Notebook/1.0"
    items = [
      {
        type = 1 # markdown
        content = {
          json = "## Estimated Resource Group Cost\n\nAggregate estimated usage cost for the **${data.azurerm_resource_group.rg.name}** Resource Group, current billing period-to-date. **This figure is an estimate** - Azure Cost Management data can lag final reconciled billing by up to a few days, and it automatically reflects whatever resources currently exist in the group (no per-resource configuration)."
        }
        name = "cost-estimate-header"
      },
      {
        type = 3 # query
        content = {
          version = "CustomEndpoint/1.0"
          query = jsonencode({
            type = "Microsoft.CostManagement/query"
            properties = {
              scope     = data.azurerm_resource_group.rg.id
              type      = "ActualCost"
              timeframe = "MonthToDate"
              dataset = {
                granularity = "None"
                aggregation = {
                  totalCost = { name = "PreTaxCost", function = "Sum" }
                }
              }
            }
          })
          size                    = 3 # card visualization
          queryType               = 8 # ARM
          resourceType            = "microsoft.costmanagement/query"
          crossComponentResources = [data.azurerm_resource_group.rg.id]
        }
        name = "cost-estimate-query"
      }
    ]
    isLocked = false
  })
}
