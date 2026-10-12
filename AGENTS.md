# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Greenfield and not yet scaffolded: no source, `package.json`, or tooling exists yet. Update this file with real build/lint/test commands and architecture once the scaffold lands.

## Purpose

A personal MCP (Model Context Protocol) server, written in Node.js + TypeScript, that lets the Claude mobile app talk to the owner's Garmin account. It fetches health data from Garmin and serves it back to Claude through MCP tools.

## Migration from legacy projects

The scaffold is meant to reuse code and knowledge from two existing sibling projects (to be identified by the user; likely candidates under `/home/jackisback/WslCode/garmin/` include `my-garmin-api`). Once this project is up and running, those two projects will be deleted, so anything worth keeping must be ported here rather than referenced in place. Do not add imports or paths pointing at the sibling projects.
