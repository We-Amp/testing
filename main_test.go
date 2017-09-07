package main

import (
	"testing"

	"github.com/franela/goblin"
)

func Test(t *testing.T) {
	g := goblin.Goblin(t)
	g.Describe("Simple Initial test", func() {
		// Passing Test
		g.It("Should start server", func() {
			output := StartTest()
			g.Assert(output).Equal("Hello World\n")
		})
	})
}
