-- Bootstrap lazy.nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
  vim.fn.system({
    "git", "clone", "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable", lazypath
  })
end
vim.opt.rtp:prepend(lazypath)

-- Basic settings
vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.tabstop = 2
vim.opt.shiftwidth = 2
vim.opt.expandtab = true
vim.opt.smartindent = true
vim.opt.wrap = false
vim.opt.termguicolors = true
vim.opt.signcolumn = "yes"
vim.opt.cursorline = true
vim.opt.scrolloff = 8
vim.opt.clipboard = "unnamedplus"
vim.g.mapleader = " "

-- Keymaps
vim.keymap.set("n", "<leader>e", ":Neotree toggle<CR>")
vim.keymap.set("n", "<leader>ff", ":Telescope find_files<CR>")
vim.keymap.set("n", "<leader>fg", ":Telescope live_grep<CR>")
vim.keymap.set("n", "<leader>fb", ":Telescope buffers<CR>")
vim.keymap.set("n", "<C-h>", "<C-w>h")
vim.keymap.set("n", "<C-l>", "<C-w>l")
vim.keymap.set("n", "<C-j>", "<C-w>j")
vim.keymap.set("n", "<C-k>", "<C-w>k")
vim.keymap.set("n", "<leader>f", function() require("conform").format({ async = true }) end)

-- Plugins
require("lazy").setup({
  -- Colorscheme
  {
    "folke/tokyonight.nvim",
    lazy = false,
    priority = 1000,
    config = function()
      require("tokyonight").setup({
        style = "night",
        transparent = true,
        colors = {
          bg = "#0D0D0D",
          bg_dark = "#0D0D0D",
          bg_float = "#242833",
          bg_popup = "#242833",
          bg_sidebar = "#0D0D0D",
          bg_statusline = "#242833",
          border = "#F27C38",
          fg = "#C8CDB8",
          fg_dark = "#787F56",
          comment = "#787F56",
          cyan = "#36D3D4",
          blue = "#4a7a8a",
          green = "#787F56",
          orange = "#F27C38",
          yellow = "#E8A020",
          red = "#C4501A",
          magenta = "#9A7060",
        },
        on_highlights = function(hl, c)
          hl.CursorLine = { bg = "#1a1a14" }
          hl.LineNr = { fg = "#787F56" }
          hl.CursorLineNr = { fg = "#F27C38" }
          hl.BorderColor = { fg = "#F27C38" }
        end
      })
      vim.cmd("colorscheme tokyonight-night")
    end
  },

  -- File tree
  {
    "nvim-neo-tree/neo-tree.nvim",
    branch = "v3.x",
    dependencies = {
      "nvim-lua/plenary.nvim",
      "nvim-tree/nvim-web-devicons",
      "MunifTanjim/nui.nvim",
    }
  },

  -- Syntax highlighting
  {
    "nvim-treesitter/nvim-treesitter",
    build = ":TSUpdate",
    config = function()
      vim.treesitter.language.setup = vim.treesitter.language.setup or function() end
      require("nvim-treesitter").setup({
        ensure_installed = { "lua", "python", "javascript", "typescript", "html", "css", "rust", "cpp", "bash", "json", "markdown" },
        highlight = { enable = true },
        indent = { enable = true }
      })
    end
  },
  {
    "lervag/vimtex",
    lazy = false, -- we don't want to lazy load VimTeX
    -- tag = "v2.15", -- uncomment to pin to a specific release
    init = function()
      -- VimTeX configuration goes here, e.g.
      vim.g.vimtex_view_method = "zathura"
    end
  },
  -- Fuzzy finder
  {
    "nvim-telescope/telescope.nvim",
    dependencies = { "nvim-lua/plenary.nvim" }
  },

  -- LSP
  {
    "neovim/nvim-lspconfig",
    dependencies = {
      "williamboman/mason.nvim",
      "williamboman/mason-lspconfig.nvim",
    },
    config = function()
      require("mason").setup()
      require("mason-lspconfig").setup({
        ensure_installed = { "lua_ls", "pyright", "ts_ls", "html", "cssls", "rust_analyzer", "clangd" },
      })
      vim.lsp.config("lua_ls", {})
      vim.lsp.config("pyright", {})
      vim.lsp.config("ts_ls", {})
      vim.lsp.config("html", {})
      vim.lsp.config("cssls", {})
      vim.lsp.config("rust_analyzer", {})
      vim.lsp.config("clangd", {})
      vim.lsp.enable({ "lua_ls", "pyright", "ts_ls", "html", "cssls", "rust_analyzer", "clangd" })
    end
  },

  -- Autocompletion
  {
    "hrsh7th/nvim-cmp",
    dependencies = {
      "hrsh7th/cmp-nvim-lsp",
      "hrsh7th/cmp-buffer",
      "hrsh7th/cmp-path",
      "L3MON4D3/LuaSnip",
      "saadparwaiz1/cmp_luasnip"
    },
    config = function()
      local cmp = require("cmp")
      cmp.setup({
        snippet = {
          expand = function(args)
            require("luasnip").lsp_expand(args.body)
          end
        },
        mapping = cmp.mapping.preset.insert({
          ["<C-Space>"] = cmp.mapping.complete(),
          ["<CR>"] = cmp.mapping.confirm({ select = true }),
          ["<Tab>"] = cmp.mapping.select_next_item(),
          ["<S-Tab>"] = cmp.mapping.select_prev_item(),
        }),
        sources = {
          { name = "nvim_lsp" },
          { name = "luasnip" },
          { name = "buffer" },
          { name = "path" }
        }
      })
    end
  },

  -- Formatter
  {
    "stevearc/conform.nvim",
    config = function()
      require("conform").setup({
        formatters_by_ft = {
          python     = { "black" },
          javascript = { "prettier" },
          typescript = { "prettier" },
          html       = { "prettier" },
          css        = { "prettier" },
          rust       = { "rustfmt" },
          cpp        = { "clang_format" },
          lua        = { "stylua" },
        },
        format_on_save = {
          timeout_ms = 500,
          lsp_fallback = true,
        },
      })
    end
  },

  -- Statusline
  {
    "nvim-lualine/lualine.nvim",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
      require("lualine").setup({
        options = {
          theme = {
            normal   = { c = { fg = "#C8CDB8", bg = "#242833" } },
            insert   = { c = { fg = "#E8A020", bg = "#242833" } },
            visual   = { c = { fg = "#F27C38", bg = "#242833" } },
            replace  = { c = { fg = "#C4501A", bg = "#242833" } },
            command  = { c = { fg = "#787F56", bg = "#242833" } },
            inactive = { c = { fg = "#787F56", bg = "#0D0D0D" } },
          },
          section_separators = { left = "", right = "" },
          component_separators = { left = "│", right = "│" },
        }
      })
    end
  },

  -- Git signs
  {
    "lewis6991/gitsigns.nvim",
    config = function()
      require("gitsigns").setup()
    end
  },

  -- Auto pairs
  {
    "windwp/nvim-autopairs",
    config = function()
      require("nvim-autopairs").setup()
    end
  },

  -- Comment
  {
    "numToStr/Comment.nvim",
    config = function()
      require("Comment").setup()
    end
  },

  -- Indent guides
  {
    "lukas-reineke/indent-blankline.nvim",
    main = "ibl",
    config = function()
      require("ibl").setup()
    end
  },

  -- Bufferline
  {
    "akinsho/bufferline.nvim",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
      require("bufferline").setup()
    end
  }
})

vim.api.nvim_create_autocmd("VimEnter", {
  callback = function()
    io.stdout:write("\027[>1u")
  end,
})
vim.api.nvim_create_autocmd("VimLeavePre", {
  callback = function()
    io.stdout:write("\027[<1u")
  end,
})
